#!/usr/bin/env python3
"""Build offline FlexHook selection/identity oracle result trees.

The script never feeds GT to FlexHook.  It only creates TrackEval-compatible
counterfactual result directories from the frozen Temp-NeuralSORT candidate
pool and the Refer-KITTI-v2 gt_template files:

* O1: keep the original candidate row and ID for one-to-one IoU matches;
* O2: keep the same matched candidate boxes but replace the ID by the matched
  GT ID, which is an offline identity oracle;
* O3: emit the GT rows themselves as an evaluator sanity check.

The output is intentionally separate from the official model output.  It is
not a model prediction and must not be used as a training or inference input.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class MotRow:
    frame: int
    track_id: int
    x: float
    y: float
    w: float
    h: float
    fields: tuple[str, ...]

    @property
    def xyxy(self) -> tuple[float, float, float, float]:
        return self.x, self.y, self.x + self.w, self.y + self.h


def read_mot(path: Path) -> list[MotRow]:
    rows: list[MotRow] = []
    if not path.is_file() or path.stat().st_size == 0:
        return rows
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        fields = tuple(part.strip() for part in raw.split(","))
        if len(fields) < 6:
            continue
        try:
            frame = int(float(fields[0]))
            track_id = int(float(fields[1]))
            x, y, w, h = (float(value) for value in fields[2:6])
        except ValueError:
            continue
        rows.append(MotRow(frame, track_id, x, y, w, h, fields))
    return rows


def read_gt(path: Path) -> list[MotRow]:
    rows: list[MotRow] = []
    if not path.is_file():
        raise FileNotFoundError(path)
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        fields = tuple(part.strip() for part in raw.split(","))
        if len(fields) < 6:
            continue
        try:
            frame = int(float(fields[0]))
            track_id = int(float(fields[1]))
            # Refer-KITTI gt_template follows MOT x,y,width,height, just like
            # the tracker files.  The evaluator converts these columns to
            # xyxy internally when it computes IoU.
            x, y, w, h = (float(value) for value in fields[2:6])
        except ValueError:
            continue
        rows.append(MotRow(frame, track_id, x, y, w, h, fields))
    return rows


def iou(left: MotRow, right: MotRow) -> float:
    lx1, ly1, lx2, ly2 = left.xyxy
    rx1, ry1, rx2, ry2 = right.xyxy
    ix1, iy1 = max(lx1, rx1), max(ly1, ry1)
    ix2, iy2 = min(lx2, rx2), min(ly2, ry2)
    intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if intersection <= 0:
        return 0.0
    left_area = max(0.0, lx2 - lx1) * max(0.0, ly2 - ly1)
    right_area = max(0.0, rx2 - rx1) * max(0.0, ry2 - ry1)
    union = left_area + right_area - intersection
    return intersection / union if union > 0 else 0.0


def one_to_one_matches(
    gt_rows: list[MotRow], candidate_rows: list[MotRow], threshold: float
) -> dict[int, tuple[MotRow, float]]:
    pairs: list[tuple[float, int, int]] = []
    for gt_index, gt_row in enumerate(gt_rows):
        for candidate_index, candidate_row in enumerate(candidate_rows):
            overlap = iou(gt_row, candidate_row)
            if overlap >= threshold:
                pairs.append((overlap, gt_index, candidate_index))
    pairs.sort(key=lambda item: (-item[0], item[1], item[2]))
    used_gt: set[int] = set()
    used_candidates: set[int] = set()
    matches: dict[int, tuple[MotRow, float]] = {}
    for overlap, gt_index, candidate_index in pairs:
        if gt_index in used_gt or candidate_index in used_candidates:
            continue
        used_gt.add(gt_index)
        used_candidates.add(candidate_index)
        matches[gt_index] = (candidate_rows[candidate_index], overlap)
    return matches


def candidate_pool(track_root: Path, video: str) -> dict[int, list[MotRow]]:
    cars = read_mot(track_root / video / "car" / "predict.txt")
    pedestrians = read_mot(track_root / video / "pedestrian" / "predict.txt")
    max_car_id = max((row.track_id for row in cars), default=0)
    # This is the exact offset used by FlexHook data/mydataloader.py and
    # test_utils.py when the two tracker classes are merged.
    pedestrians = [
        MotRow(row.frame, row.track_id + max_car_id, row.x, row.y, row.w, row.h,
               (row.fields[0], str(row.track_id + max_car_id), *row.fields[2:]))
        for row in pedestrians
    ]
    by_frame: dict[int, list[MotRow]] = defaultdict(list)
    for row in (*cars, *pedestrians):
        by_frame[row.frame].append(row)
    return dict(by_frame)


def candidate_line(row: MotRow, new_id: int | None = None) -> str:
    fields = list(row.fields)
    fields[1] = str(row.track_id if new_id is None else new_id)
    return ",".join(fields)


def gt_line(row: MotRow) -> str:
    return ",".join(row.fields)


def prepare_output(root: Path, mode: str, gt_root: Path, force: bool) -> None:
    if root.exists():
        if not force:
            raise SystemExit(f"output exists; use --force only for generated output: {root}")
        shutil.rmtree(root)
    root.mkdir(parents=True)
    (root / ".oracle_manifest").write_text(mode + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--track-root", type=Path, required=True)
    parser.add_argument("--gt-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--mode", choices=("O1", "O2", "O3"), required=True)
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    videos = sorted(path.name for path in args.gt_root.iterdir() if path.is_dir())
    if not videos:
        raise SystemExit(f"no video directories under {args.gt_root}")
    prepare_output(args.output_root, args.mode, args.gt_root, args.force)

    total_gt = 0
    total_output = 0
    total_matched = 0
    expression_count = 0
    for video in videos:
        candidates = candidate_pool(args.track_root, video)
        for gt_path in sorted((args.gt_root / video).glob("*/gt.txt")):
            expression = gt_path.parent.name
            gt_rows = read_gt(gt_path)
            out_dir = args.output_root / video / expression
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "gt.txt").symlink_to(gt_path.resolve())
            total_gt += len(gt_rows)
            expression_count += 1

            if args.mode == "O3":
                output_lines = [gt_line(row) for row in gt_rows]
            else:
                matches: dict[int, tuple[MotRow, float]] = {}
                gt_by_frame: dict[int, list[tuple[int, MotRow]]] = defaultdict(list)
                for gt_index, row in enumerate(gt_rows):
                    gt_by_frame[row.frame].append((gt_index, row))
                for frame, indexed_gt in gt_by_frame.items():
                    local_matches = one_to_one_matches(
                        [row for _, row in indexed_gt], candidates.get(frame, []), args.iou_threshold
                    )
                    for local_index, match in local_matches.items():
                        matches[indexed_gt[local_index][0]] = match
                total_matched += len(matches)
                output_lines = []
                for gt_index, (candidate, _overlap) in sorted(matches.items()):
                    new_id = gt_rows[gt_index].track_id if args.mode == "O2" else None
                    output_lines.append(candidate_line(candidate, new_id))

            (out_dir / "predict.txt").write_text(
                "" if not output_lines else "\n".join(output_lines) + "\n", encoding="utf-8"
            )
            total_output += len(output_lines)

    manifest = {
        "mode": args.mode,
        "iou_threshold": args.iou_threshold if args.mode != "O3" else None,
        "track_root": str(args.track_root),
        "gt_root": str(args.gt_root),
        "videos": videos,
        "expressions": expression_count,
        "gt_rows": total_gt,
        "matched_rows": total_matched,
        "output_rows": total_output,
        "caveat": "Offline counterfactual; GT never enters FlexHook inference.",
    }
    (args.output_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
