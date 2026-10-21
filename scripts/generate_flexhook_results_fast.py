#!/usr/bin/env python3
"""Materialize FlexHook's official result files without SSHFS inner-loop I/O.

This is a drop-in implementation of ``test_utils.generate_final_results`` for
the Refer-KITTI-v2 tuple.  It consumes the already sealed official
``result.json`` (raw two-class logits), preloads the expression sentences once,
and writes the same candidate boxes/IDs selected by ``argmax(score) > 0``.
It never reads GT for a decision; GT files are only linked for TrackEval.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import defaultdict
from pathlib import Path


FRAMES = {"0005": (0, 296), "0011": (0, 372), "0013": (0, 339), "0019": (0, 1058)}


def load_tracker(path: Path, id_offset: int = 0) -> dict[tuple[int, int], str]:
    rows: dict[tuple[int, int], str] = {}
    if not path.is_file() or path.stat().st_size == 0:
        return rows
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        fields = [part.strip() for part in raw.split(",")]
        if len(fields) < 6:
            continue
        try:
            frame = int(float(fields[0]))
            track_id = int(float(fields[1])) + id_offset
            float(fields[2])
            float(fields[3])
            float(fields[4])
            float(fields[5])
        except ValueError:
            continue
        fields[1] = str(track_id)
        rows[(frame, track_id)] = ",".join(fields)
    return rows


def load_candidates(track_root: Path, video: str) -> dict[tuple[int, int], str]:
    car_path = track_root / video / "car" / "predict.txt"
    ped_path = track_root / video / "pedestrian" / "predict.txt"
    cars = load_tracker(car_path)
    car_ids = [key[1] for key in cars]
    max_car_id = max(car_ids, default=0)
    pedestrians = load_tracker(ped_path, id_offset=max_car_id)
    result = dict(cars)
    result.update(pedestrians)
    return result


def load_expressions(expression_root: Path, video: str) -> tuple[list[str], dict[str, list[str]]]:
    names: list[str] = []
    sentence_to_names: dict[str, list[str]] = defaultdict(list)
    for path in sorted((expression_root / video).glob("*.json")):
        name = path.stem
        sentence = json.loads(path.read_text(encoding="utf-8"))["sentence"]
        names.append(name)
        sentence_to_names[sentence].append(name)
    return names, dict(sentence_to_names)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-json", type=Path, required=True)
    parser.add_argument("--track-root", type=Path, required=True)
    parser.add_argument("--expression-root", type=Path, required=True)
    parser.add_argument("--gt-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.output_root.exists():
        if not args.force:
            raise SystemExit(f"output exists; use --force for generated output: {args.output_root}")
        shutil.rmtree(args.output_root)
    args.output_root.mkdir(parents=True)

    result = json.loads(args.result_json.read_text(encoding="utf-8"))
    totals = {"videos": 0, "expressions": 0, "positive_rows": 0, "candidate_rows": 0, "missing_candidates": 0}
    per_video: dict[str, dict[str, int]] = {}

    for video in sorted(result):
        if video not in FRAMES:
            raise SystemExit(f"unsupported Refer-KITTI-v2 video: {video}")
        totals["videos"] += 1
        expression_names, sentence_to_names = load_expressions(args.expression_root, video)
        candidates = load_candidates(args.track_root, video)
        totals["expressions"] += len(expression_names)
        video_counts = {"expressions": len(expression_names), "positive_rows": 0, "missing_candidates": 0}

        output_video = args.output_root / video
        output_video.mkdir(parents=True, exist_ok=True)
        lines_by_expression: dict[str, list[str]] = {name: [] for name in expression_names}

        # Materialize every GT link up front, including expressions with no
        # selected candidates; TrackEval requires an empty predict.txt file in
        # that case rather than a missing path.
        for name in expression_names:
            output_expression = output_video / name
            output_expression.mkdir(parents=True, exist_ok=True)
            gt_path = args.gt_root / video / name / "gt.txt"
            (output_expression / "gt.txt").symlink_to(gt_path.resolve())

        for object_id, frame_dict in result[video].items():
            object_id_int = int(object_id)
            for frame_key, score_dict in frame_dict.items():
                frame0 = int(frame_key)
                frame1 = frame0 + 1
                if not (FRAMES[video][0] <= frame0 <= FRAMES[video][1]):
                    continue
                candidate_line = candidates.get((frame1, object_id_int))
                if candidate_line is None:
                    video_counts["missing_candidates"] += 1
                    totals["missing_candidates"] += 1
                    continue
                totals["candidate_rows"] += 1
                for sentence, score in score_dict.items():
                    # numpy.argmax([negative, positive]) > 0, without importing
                    # numpy for this purely scalar decision.
                    if not score or max(range(len(score)), key=lambda index: score[index]) <= 0:
                        continue
                    for expression_name in sentence_to_names.get(sentence, []):
                        lines_by_expression[expression_name].append(candidate_line)
                        totals["positive_rows"] += 1
                        video_counts["positive_rows"] += 1

        for name in expression_names:
            (output_video / name / "predict.txt").write_text(
                "" if not lines_by_expression[name] else "\n".join(lines_by_expression[name]) + "\n",
                encoding="utf-8",
            )
        per_video[video] = video_counts

    manifest = {
        "protocol": "FlexHook official test_utils.generate_final_results semantics, preloaded expression mapping",
        "result_json": str(args.result_json),
        "track_root": str(args.track_root),
        "expression_root": str(args.expression_root),
        "gt_root": str(args.gt_root),
        "output_root": str(args.output_root),
        "decision": "argmax(raw_two_class_score)>0; original candidate bbox and merged candidate ID",
        "totals": totals,
        "per_video": per_video,
        "caveat": "GT is linked for evaluation only and never enters the model decision.",
    }
    (args.output_root / "generation_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
