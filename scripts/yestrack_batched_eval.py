#!/usr/bin/env python3
"""Batched YesTrack inference using the official scoring/evaluation semantics.

The released ``llm_eval_from_mot.py`` processes one frame at a time.  That is
faithful but very slow on the local V100 host because the Qwen-VL forward is
called once per frame.  This isolated runner keeps the same model, prompts,
crop geometry, selective video refinement, TCP, and TRP state machine, while
batching independent primary/refinement samples across frames of one
expression.  It is intended for reproduction on machines where the official
script is otherwise impractical; the original checkout is never modified.

The runner imports helper functions from an isolated YesTrack checkout at
runtime.  Set ``PYTHONPATH`` so that checkout is first, as in the documented
run receipt.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import time
from collections import deque
from typing import Dict, List, Optional, Sequence, Tuple

import torch
import torch.distributed as dist


Box = Tuple[float, float, float, float]
Det = Tuple[int, float, float, float, float, float]


def _setup_distributed() -> Tuple[int, int, int]:
    if "RANK" in os.environ and "WORLD_SIZE" in os.environ:
        rank = int(os.environ["RANK"])
        world_size = int(os.environ["WORLD_SIZE"])
        local_rank = int(os.environ.get("LOCAL_RANK", 0))
        if not dist.is_initialized():
            dist.init_process_group(backend="nccl")
        torch.cuda.set_device(local_rank)
        return rank, world_size, local_rank
    return 0, 1, 0


def _main_process() -> bool:
    return not dist.is_initialized() or dist.get_rank() == 0


def _chunked(items: Sequence, size: int):
    n = max(1, int(size))
    for start in range(0, len(items), n):
        yield items[start : start + n]


def _build_tasks(results_root: str) -> List[Tuple[str, str, str]]:
    tasks: List[Tuple[str, str, str]] = []
    for seq in sorted(
        d for d in os.listdir(results_root) if os.path.isdir(os.path.join(results_root, d))
    ):
        seq_dir = os.path.join(results_root, seq)
        for expr_dir in sorted(
            d for d in os.listdir(seq_dir) if os.path.isdir(os.path.join(seq_dir, d))
        ):
            tasks.append((seq, expr_dir, os.path.join(seq_dir, expr_dir, "predict.txt")))
    return tasks


def _image_path(img_seq_dir: str, frame: int, mot_frame_start_one: int, image_frame_start_one: int) -> str:
    base = frame - 1 if int(mot_frame_start_one) == 1 else frame
    if int(image_frame_start_one) == 1:
        base += 1
    return os.path.join(img_seq_dir, f"{int(base):06d}.png")


def _make_video_item(
    *,
    tid: int,
    frame: int,
    id_to_traj: Dict[int, List[Tuple[int, Box]]],
    frame_index_by_tid: Dict[int, Dict[int, int]],
    img_seq_dir: str,
    mot_frame_start_one: int,
    image_frame_start_one: int,
    video_n_frames: int,
) -> Tuple[List[str], List[Box]]:
    traj = id_to_traj.get(int(tid), [])
    idx = frame_index_by_tid.get(int(tid), {}).get(int(frame))
    paths: List[str] = []
    boxes: List[Box] = []
    if idx is not None:
        start = max(0, int(idx) - int(video_n_frames) + 1)
        for f_tr, box in traj[start : int(idx) + 1]:
            paths.append(_image_path(img_seq_dir, f_tr, mot_frame_start_one, image_frame_start_one))
            boxes.append(box)
    return paths, boxes


def _eval_one_task(
    *,
    task: Tuple[str, str, str],
    args,
    model,
    processor,
    device: torch.device,
    yes_id: int,
    no_id: int,
    mot,
) -> int:
    """Run one expression while batching independent model inputs.

    Returns the number of output rows.  The stateful output logic is applied in
    frame order after all primary/refinement probabilities have been computed,
    so TRP/TCP remain causal and identical to the official implementation.
    """

    seq, expr_dirname, mot_file = task
    if not os.path.isfile(mot_file):
        raise FileNotFoundError(f"{seq}/{expr_dirname} missing {mot_file}")

    frame_to_dets = mot._load_mot_file(mot_file, frame_offset=int(args.frame_offset))
    img_seq_dir = os.path.join(args.data_root, "KITTI", "training", "image_02", seq)
    if not os.path.isdir(img_seq_dir):
        alt = os.path.join(args.data_root, "training", "image_02", seq)
        img_seq_dir = alt if os.path.isdir(alt) else img_seq_dir
    if not os.path.isdir(img_seq_dir):
        raise FileNotFoundError(f"image sequence directory not found: {img_seq_dir}")

    out_seq_expr_dir = os.path.join(args.output_root, seq, expr_dirname)
    os.makedirs(out_seq_expr_dir, exist_ok=True)
    out_path = os.path.join(out_seq_expr_dir, "predict_with_conf.txt")

    if args.resume and os.path.isfile(out_path) and frame_to_dets:
        last = mot._max_frame_in_mot_output(out_path)
        if last is not None and int(last) >= max(frame_to_dets):
            return sum(1 for line in open(out_path, encoding="utf-8") if line.strip())

    id_to_traj: Dict[int, List[Tuple[int, Box]]] = {}
    for frame, dets in frame_to_dets.items():
        for tid, x, y, w, h, _score in dets:
            id_to_traj.setdefault(int(tid), []).append((int(frame), (x, y, w, h)))
    for tid in id_to_traj:
        id_to_traj[tid].sort(key=lambda z: z[0])
    frame_index_by_tid = {
        tid: {frame: idx for idx, (frame, _box) in enumerate(traj)}
        for tid, traj in id_to_traj.items()
    }

    sentence = mot._natural_sentence_from_dirname(expr_dirname)
    frames = sorted(frame_to_dets)

    # Primary samples are keyed by (frame, detection index).  We determine the
    # TRP schedule using only ID presence; actual confidence values are not
    # needed until the causal output pass below.
    primary_items = []
    primary_indices_by_frame: Dict[int, List[int]] = {}
    seen_ids = set()
    for frame_counter, frame in enumerate(frames):
        dets = frame_to_dets[frame]
        full = int(args.infer_every_n_frames) <= 1 or frame_counter % int(args.infer_every_n_frames) == 0
        indices = list(range(len(dets))) if full else [
            i for i, det in enumerate(dets) if int(det[0]) not in seen_ids
        ]
        primary_indices_by_frame[frame] = indices
        if indices:
            img_path = _image_path(img_seq_dir, frame, args.mot_frame_start_one, args.image_frame_start_one)
            boxes = [(dets[i][1], dets[i][2], dets[i][3], dets[i][4]) for i in indices]
            patches, width, height = mot._prepare_patches_for_frame(
                img_path=img_path,
                dets_xywh=boxes,
                image_size=args.image_size,
                margin_ratio=args.margin_ratio,
                margin_px=args.margin_px,
                min_side=args.min_side,
                preprocess_workers=args.preprocess_workers,
                context=f"seq={seq} expr={expr_dirname} frame={frame}",
            )
            for local_idx, det_idx in enumerate(indices):
                _tid, x, y, w, h, _score = dets[det_idx]
                cx = x + 0.5 * w
                cy = y + 0.5 * h
                coord = f"{max(0.0, min(1.0, cx / float(width))):.3f} {max(0.0, min(1.0, cy / float(height))):.3f}"
                prompt = args.prompt_single_tpl.format(coord=coord, sentence=sentence)
                primary_items.append((frame, det_idx, patches[local_idx], prompt))
        seen_ids.update(int(d[0]) for d in dets)

    primary_probs: Dict[Tuple[int, int], float] = {}
    with torch.no_grad():
        for batch in _chunked(primary_items, args.batch_size):
            patches = [item[2] for item in batch]
            prompts = [item[3] for item in batch]
            probs = mot._forward_probs_for_patches(
                model=model,
                processor=processor,
                device=device,
                patches=patches,
                prompts=prompts,
                yes_id=yes_id,
                no_id=no_id,
                context=f"batched-primary seq={seq} expr={expr_dirname}",
            )
            for item, prob in zip(batch, probs):
                primary_probs[(int(item[0]), int(item[1]))] = float(prob)

    if args.progress:
        print(f"[BATCH] {seq}/{expr_dirname} primary={len(primary_items)}", flush=True)

    # Selective multi-frame refinement uses only samples that had a primary
    # inference on this frame and fall in the official [lower, upper) interval.
    refine_items = []
    for frame in ([] if args.disable_refine else frames):
        dets = frame_to_dets[frame]
        for det_idx in primary_indices_by_frame.get(frame, []):
            p = primary_probs[(int(frame), int(det_idx))]
            if not (float(args.re_refer_lower) <= p < float(args.re_refer_thresh)):
                continue
            tid, x, y, w, h, _score = dets[det_idx]
            paths, boxes = _make_video_item(
                tid=int(tid), frame=int(frame), id_to_traj=id_to_traj,
                frame_index_by_tid=frame_index_by_tid, img_seq_dir=img_seq_dir,
                mot_frame_start_one=args.mot_frame_start_one,
                image_frame_start_one=args.image_frame_start_one,
                video_n_frames=args.video_n_frames,
            )
            if not paths:
                paths = [_image_path(img_seq_dir, frame, args.mot_frame_start_one, args.image_frame_start_one)]
                boxes = [(x, y, w, h)]
            # The image size is stable for a sequence; use the official helper
            # path indirectly by deriving normalized coordinates from KITTI's
            # documented 1242x375 fallback only when opening is unavailable.
            from PIL import Image
            with Image.open(paths[-1]) as im:
                width, height = im.size
            cx = x + 0.5 * w
            cy = y + 0.5 * h
            coord = f"{max(0.0, min(1.0, cx / float(width))):.3f} {max(0.0, min(1.0, cy / float(height))):.3f}"
            prompt = args.prompt_video_tpl.format(coord=coord, sentence=sentence)
            refine_items.append((frame, det_idx, paths, boxes, prompt))

    refined_probs: Dict[Tuple[int, int], float] = {}
    with torch.no_grad():
        for batch in _chunked(refine_items, args.batch_size):
            probs = mot._forward_probs_for_detections_video(
                model=model,
                processor=processor,
                device=device,
                image_paths_per_sample=[item[2] for item in batch],
                dets_per_sample=[item[3] for item in batch],
                prompts=[item[4] for item in batch],
                yes_id=yes_id,
                no_id=no_id,
                image_size=args.image_size,
                margin_ratio=args.margin_ratio,
                margin_px=args.margin_px,
                min_side=args.min_side,
                preprocess_workers=args.preprocess_workers,
                context=f"batched-refine seq={seq} expr={expr_dirname}",
            )
            for item, prob in zip(batch, probs):
                refined_probs[(int(item[0]), int(item[1]))] = float(prob)

    if args.progress:
        print(f"[BATCH] {seq}/{expr_dirname} refine={len(refine_items)}", flush=True)

    # Causal output pass: reuse previous ID confidence on TRP frames, apply
    # refinement, then TCP based only on prior output history.
    lines_out: List[str] = []
    last_conf_by_tid: Dict[int, float] = {}
    stability_cache: Dict[int, deque] = {}
    for frame in frames:
        dets = frame_to_dets[frame]
        primary_indices = set(primary_indices_by_frame.get(frame, []))
        probs: List[float] = []
        for det_idx, det in enumerate(dets):
            tid = int(det[0])
            if det_idx in primary_indices:
                p = primary_probs[(int(frame), int(det_idx))]
                if (int(frame), int(det_idx)) in refined_probs:
                    p = refined_probs[(int(frame), int(det_idx))]
            else:
                if tid not in last_conf_by_tid:
                    raise RuntimeError(f"TRP state missing for seq={seq} expr={expr_dirname} frame={frame} tid={tid}")
                p = last_conf_by_tid[tid]
            probs.append(float(p))

        if args.stability_enable:
            win = max(1, int(args.stability_window))
            for det_idx, det in enumerate(dets):
                tid = int(det[0])
                history = stability_cache.get(tid)
                if history is None:
                    history = deque(maxlen=win)
                    stability_cache[tid] = history
                if len(history) >= win and all(v >= float(args.stability_thresh) for v in history):
                    probs[det_idx] = min(1.0, probs[det_idx] + float(args.stability_boost))
                history.append(float(probs[det_idx]))

        for det, p in zip(dets, probs):
            tid, x, y, w, h, _score = det
            last_conf_by_tid[int(tid)] = float(p)
            lines_out.append(f"{int(frame)},{int(tid)},{int(x)},{int(y)},{int(w)},{int(h)},{float(p):.6f}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out))
    return len(lines_out)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model_name", required=True)
    p.add_argument("--lora_path", required=True)
    p.add_argument("--data_root", required=True)
    p.add_argument("--results_root", required=True)
    p.add_argument("--output_root", required=True)
    p.add_argument("--batch_size", type=int, default=8)
    p.add_argument("--max_tasks", type=int, default=0, help="debug limit; 0 means all tasks")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--use_4bit", action="store_true")
    p.add_argument("--fp16", action="store_true")
    p.add_argument("--mot_frame_start_one", type=int, default=1)
    p.add_argument("--image_frame_start_one", type=int, default=0)
    p.add_argument("--frame_offset", type=int, default=0)
    p.add_argument("--infer_every_n_frames", type=int, default=4)
    p.add_argument("--video_n_frames", type=int, default=4)
    p.add_argument("--image_size", type=int, default=320)
    p.add_argument("--margin_ratio", type=float, default=0.2)
    p.add_argument("--margin_px", type=int, default=None)
    p.add_argument("--min_side", type=int, default=8)
    p.add_argument("--preprocess_workers", type=int, default=4)
    p.add_argument("--re_refer_thresh", type=float, default=0.8)
    p.add_argument("--re_refer_lower", type=float, default=0.2)
    p.add_argument("--disable_refine", action="store_true")
    p.add_argument("--progress", action="store_true")
    p.add_argument("--stability_enable", action="store_true")
    p.add_argument("--stability_window", type=int, default=6)
    p.add_argument("--stability_thresh", type=float, default=0.4)
    p.add_argument("--stability_boost", type=float, default=0.3)
    p.add_argument(
        "--prompt_single_tpl",
        default="The normalized position of the car or person in the picture is <{coord}>.Determine whether this description matches this image: {sentence}. Answer Yes or No.",
    )
    p.add_argument(
        "--prompt_video_tpl",
        default="This is a short video clip of a car or person at <{coord}> across frames. The target may include motion cues; consider background and temporal context when deciding if the description matches this target: {sentence}. Answer Yes or No.",
    )
    args = p.parse_args()

    rank, world_size, local_rank = _setup_distributed()
    device = torch.device(f"cuda:{local_rank}" if torch.cuda.is_available() else "cpu")

    # Import only after PYTHONPATH has been set to the isolated YesTrack copy.
    from refer_llm import llm_eval_from_mot as mot
    from refer_llm.llm_eval import build_model_and_processor_for_eval, get_yes_no_token_ids
    from data.refer_kitti_mot import ReferKittiMOT

    model, processor, _ = build_model_and_processor_for_eval(
        model_name=args.model_name,
        use_4bit=bool(args.use_4bit),
        bf16=not bool(args.fp16),
        lora_path=args.lora_path,
    )
    model.to(device)
    model.eval()
    yes_id, no_id = get_yes_no_token_ids(processor)

    ds_all = ReferKittiMOT(
        data_root=args.data_root,
        split="all",
        load_annotation=False,
        expression_sub_dir="expression",
        labels_with_ids_sub_dir="labels_with_ids/image_02",
    )
    mot._check_expressions_match_dataset(args.data_root, args.results_root)
    tasks = _build_tasks(args.results_root)
    if args.max_tasks > 0:
        tasks = tasks[: args.max_tasks]
    os.makedirs(args.output_root, exist_ok=True)

    start = time.perf_counter()
    attempted = ok = err = rows = 0
    for idx, task in enumerate(tasks):
        if world_size > 1 and idx % world_size != rank:
            continue
        attempted += 1
        try:
            rows += _eval_one_task(
                task=task, args=args, model=model, processor=processor,
                device=device, yes_id=yes_id, no_id=no_id, mot=mot,
            )
            ok += 1
            if _main_process():
                print(f"[OK] {task[0]}/{task[1]}", flush=True)
        except Exception as exc:
            err += 1
            print(f"[ERR] {task[0]}/{task[1]}: {exc}", flush=True)

    elapsed = time.perf_counter() - start
    if world_size > 1 and dist.is_initialized():
        dist.barrier()
        vals = torch.tensor([elapsed, attempted, ok, err, rows], device=device, dtype=torch.float64)
        tmax = vals[0].clone()
        dist.all_reduce(tmax, op=dist.ReduceOp.MAX)
        dist.all_reduce(vals, op=dist.ReduceOp.SUM)
        elapsed_max = float(tmax.item())
        attempted_sum, ok_sum, err_sum, rows_sum = [int(round(v)) for v in vals[1:].tolist()]
    else:
        elapsed_max = elapsed
        attempted_sum, ok_sum, err_sum, rows_sum = attempted, ok, err, rows

    if _main_process():
        receipt = {
            "runner": "scripts/yestrack_batched_eval.py",
            "semantics": "official YesTrack prompts/crops + selective video refinement + TCP + TRP; independent samples batched",
            "world_size": int(world_size),
            "tasks_total": len(tasks),
            "attempted_tasks_sum": attempted_sum,
            "ok_tasks_sum": ok_sum,
            "err_tasks_sum": err_sum,
            "output_rows_sum": rows_sum,
            "elapsed_seconds_max": elapsed_max,
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        with open(os.path.join(args.output_root, "batched_infer_receipt.json"), "w", encoding="utf-8") as f:
            json.dump(receipt, f, ensure_ascii=False, indent=2)
        print(json.dumps(receipt, ensure_ascii=False), flush=True)

    if world_size > 1 and dist.is_initialized():
        dist.destroy_process_group()


if __name__ == "__main__":
    main()
