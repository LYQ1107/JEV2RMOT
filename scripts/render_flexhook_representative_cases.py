#!/usr/bin/env python3
"""Render 30 compact, evidence-backed FlexHook V2 error cases."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

from build_flexhook_oracle_results import candidate_pool, iou, one_to_one_matches, read_gt


RELATIONAL_WORDS = re.compile(
    r"left|right|front|back|behind|opposite|direction|same|near|side|moving|toward|away|between|"
    r"women|woman|men|man|people|person|humans|group|together|apart|next|parallel",
    re.IGNORECASE,
)


def score_for(result: dict, video: str, candidate_id: int, frame0: int, sentence: str):
    return result[video].get(str(candidate_id), {}).get(str(frame0), {}).get(sentence)


def positive(score) -> bool:
    return bool(score) and max(range(len(score)), key=lambda index: score[index]) > 0


def add_case(pool: dict[str, list[dict]], category: str, case: dict) -> None:
    pool[category].append(case)


def render_case(case: dict, image_root: Path, output_dir: Path) -> str:
    video = case["video"]
    frame0 = int(case["frame0"])
    source = image_root / video / f"{frame0:06d}.png"
    if not source.is_file():
        raise FileNotFoundError(source)
    image = Image.open(source).convert("RGB")
    draw = ImageDraw.Draw(image)

    for gt in case.get("gt_boxes", []):
        x, y, w, h = gt["bbox"]
        draw.rectangle((x, y, x + w, y + h), outline=(255, 220, 0), width=3)
        draw.text((x, max(0, y - 14)), f"GT {gt['track_id']}", fill=(255, 220, 0))
    for candidate in case.get("candidate_boxes", []):
        x, y, w, h = candidate["bbox"]
        color = (40, 220, 80) if candidate.get("selected") else (230, 70, 70)
        draw.rectangle((x, y, x + w, y + h), outline=color, width=2)
        draw.text((x, min(image.height - 14, y + h)), f"C {candidate['track_id']}", fill=color)

    banner = (
        f"{case['case_id']}  {video} f={frame0}  {case['error_type']}\n"
        f"{case['expression']}\n"
        f"yellow=GT green=selected red=non-selected"
    )
    draw.rectangle((0, 0, image.width, 48), fill=(0, 0, 0))
    draw.multiline_text((6, 4), banner, fill=(255, 255, 255), spacing=2)
    output = output_dir / f"{case['case_id']}.png"
    image.save(output)
    return str(output.resolve())


def take(pool: dict[str, list[dict]], category: str, count: int, used: set[tuple]) -> list[dict]:
    selected: list[dict] = []
    for case in pool.get(category, []):
        key = (case["video"], case["expression"], int(case["frame0"]))
        if key in used:
            continue
        used.add(key)
        selected.append(case)
        if len(selected) == count:
            break
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-json", type=Path, required=True)
    parser.add_argument("--track-root", type=Path, required=True)
    parser.add_argument("--gt-root", type=Path, required=True)
    parser.add_argument("--expression-root", type=Path, required=True)
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    result = json.loads(args.result_json.read_text(encoding="utf-8"))
    pool: dict[str, list[dict]] = defaultdict(list)

    for video in sorted(result):
        candidates_by_frame = candidate_pool(args.track_root, video)
        expression_files = sorted((args.expression_root / video).glob("*.json"))
        for expression_file in expression_files:
            expression = expression_file.stem
            sentence = json.loads(expression_file.read_text(encoding="utf-8"))["sentence"]
            gt_rows = read_gt(args.gt_root / video / expression / "gt.txt")
            by_frame: dict[int, list] = defaultdict(list)
            for index, row in enumerate(gt_rows):
                by_frame[row.frame].append((index, row))
            matched: dict[int, tuple] = {}
            for frame, indexed_gt in by_frame.items():
                local = one_to_one_matches(
                    [row for _, row in indexed_gt], candidates_by_frame.get(frame, []), 0.5
                )
                for local_index, match in local.items():
                    matched[indexed_gt[local_index][0]] = match

            def base_case(frame0: int, error_type: str, candidate=None, gt_index=None) -> dict:
                frame_gt = [
                    {"track_id": row.track_id, "bbox": [row.x, row.y, row.w, row.h]}
                    for row in gt_rows
                    if row.frame == frame0 + 1
                ]
                frame_candidates = []
                for row in candidates_by_frame.get(frame0 + 1, []):
                    score = score_for(result, video, row.track_id, frame0, sentence)
                    frame_candidates.append(
                        {
                            "track_id": row.track_id,
                            "bbox": [row.x, row.y, row.w, row.h],
                            "selected": positive(score),
                            "score": score,
                        }
                    )
                selected_ids = {match[0].track_id for index, match in matched.items() if gt_rows[index].frame == frame0 + 1}
                for item in frame_candidates:
                    item["matched_to_gt"] = item["track_id"] in selected_ids
                gt = gt_rows[gt_index] if gt_index is not None else None
                score = score_for(result, video, candidate.track_id, frame0, sentence) if candidate else None
                return {
                    "video": video,
                    "expression": expression,
                    "sentence": sentence,
                    "frame0": frame0,
                    "error_type": error_type,
                    "candidate_id": candidate.track_id if candidate else None,
                    "gt_id": gt.track_id if gt else None,
                    "score": score,
                    "final_decision": positive(score) if score is not None else None,
                    "o1_repairable": error_type in {"REFER_FALSE_NEGATIVE", "REFER_FALSE_POSITIVE"},
                    "o2_identity_repairable": error_type == "IDENTITY_ERROR_STAGE1",
                    "gt_boxes": frame_gt,
                    "candidate_boxes": frame_candidates,
                }

            for gt_index, gt_row in enumerate(gt_rows):
                match = matched.get(gt_index)
                if match is None:
                    add_case(pool, "CANDIDATE_MISSING", base_case(gt_row.frame - 1, "CANDIDATE_MISSING", gt_index=gt_index))
                    continue
                candidate = match[0]
                score = score_for(result, video, candidate.track_id, candidate.frame - 1, sentence)
                if score is not None and not positive(score):
                    add_case(pool, "REFER_FALSE_NEGATIVE", base_case(candidate.frame - 1, "REFER_FALSE_NEGATIVE", candidate, gt_index))

            matched_keys = {(row.frame - 1, match[0].track_id) for index, match in matched.items() for row in [gt_rows[index]]}
            for frame0, candidate_id, score in [
                (frame0, int(object_id), score)
                for object_id, frame_dict in result[video].items()
                for frame_key, score_dict in frame_dict.items()
                for sentence_key, score in score_dict.items()
                if sentence_key == sentence
                for frame0 in [int(frame_key)]
            ]:
                if positive(score) and (frame0, candidate_id) not in matched_keys:
                    add_case(pool, "REFER_FALSE_POSITIVE", base_case(frame0, "REFER_FALSE_POSITIVE", candidates_by_frame.get(frame0 + 1, [])[0] if candidates_by_frame.get(frame0 + 1) else None))

            # Candidate ID switch examples: a GT track maps to different
            # candidate IDs over time, independent of the stage-2 decision.
            by_target: dict[int, list[tuple[int, int]]] = defaultdict(list)
            for index, match in matched.items():
                row = gt_rows[index]
                by_target[row.track_id].append((row.frame, match[0].track_id))
            for target_id, sequence in by_target.items():
                sequence.sort()
                for (prev_frame, prev_id), (frame, candidate_id) in zip(sequence, sequence[1:]):
                    if frame == prev_frame + 1 and candidate_id != prev_id:
                        add_case(pool, "IDENTITY_ERROR_STAGE1", base_case(frame - 1, "IDENTITY_ERROR_STAGE1", next((r for r in candidates_by_frame.get(frame, []) if r.track_id == candidate_id), None)))
                        break

            if RELATIONAL_WORDS.search(sentence):
                for category in ("REFER_FALSE_NEGATIVE", "REFER_FALSE_POSITIVE", "CANDIDATE_MISSING"):
                    for candidate in pool.get(category, []):
                        if candidate["video"] == video and candidate["expression"] == expression:
                            copy = dict(candidate)
                            copy["error_type"] = "RELATIONAL_EXPRESSION_ERROR"
                            add_case(pool, "RELATIONAL_EXPRESSION_ERROR", copy)
                            break

    chosen: list[dict] = []
    used: set[tuple] = set()
    for category, count in (
        ("CANDIDATE_MISSING", 6),
        ("REFER_FALSE_NEGATIVE", 6),
        ("REFER_FALSE_POSITIVE", 6),
        ("IDENTITY_ERROR_STAGE1", 4),
        ("RELATIONAL_EXPRESSION_ERROR", 4),
    ):
        chosen.extend(take(pool, category, count, used))
    # Fill the remaining slots with distinct official errors, preserving the
    # evidence-backed category label.
    for category in ("CANDIDATE_MISSING", "REFER_FALSE_NEGATIVE", "REFER_FALSE_POSITIVE", "IDENTITY_ERROR_STAGE1"):
        if len(chosen) >= 30:
            break
        chosen.extend(take(pool, category, 30 - len(chosen), used))

    cases = []
    for index, case in enumerate(chosen[:30], start=1):
        case = dict(case)
        case["case_id"] = f"case_{index:02d}"
        case["image"] = render_case(case, args.image_root, args.output_dir)
        cases.append(case)

    payload = {
        "status": "COMPLETE" if len(cases) == 30 else "PARTIAL",
        "official_case_count": len(cases),
        "required_case_count": 30,
        "protocol": "FlexHook Refer-KITTI-V2 official raw output + fixed candidate + GT offline attribution",
        "image_dir": str(args.output_dir.resolve()),
        "caveat": "Images are local ignored artifacts; GT is used only for offline labels, never for O0 inference.",
        "cases": cases,
    }
    args.manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "cases": len(cases)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
