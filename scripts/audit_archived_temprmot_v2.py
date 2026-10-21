#!/usr/bin/env python3
"""Audit the archived TempRMOT V2 result tree without treating it as a target baseline.

The archived tree is useful for checking file schemas and historical coverage, but it
is not a YesTrack/FlexHook candidate source.  This script therefore writes explicitly
labelled auxiliary tables only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def rows(path: Path) -> Iterable[List[str]]:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        for row in csv.reader(handle):
            if row and any(cell.strip() for cell in row):
                yield row


def file_stats(path: Path, hash_files: bool = False) -> Dict[str, object]:
    frame_ids = set()
    object_ids = set()
    columns = Counter()
    count = 0
    bad_rows = 0
    min_frame = None
    max_frame = None
    for row in rows(path):
        count += 1
        columns[len(row)] += 1
        try:
            frame = int(float(row[0]))
            object_id = int(float(row[1]))
            frame_ids.add(frame)
            object_ids.add(object_id)
            min_frame = frame if min_frame is None else min(min_frame, frame)
            max_frame = frame if max_frame is None else max(max_frame, frame)
        except (IndexError, TypeError, ValueError):
            bad_rows += 1
    digest = hashlib.sha256(path.read_bytes()).hexdigest() if hash_files else "not-computed"
    return {
        "rows": count,
        "frames": len(frame_ids),
        "ids": len(object_ids),
        "min_frame": "" if min_frame is None else min_frame,
        "max_frame": "" if max_frame is None else max_frame,
        "column_shapes": ";".join(f"{key}:{value}" for key, value in sorted(columns.items())),
        "bad_rows": bad_rows,
        "bytes": path.stat().st_size,
        "sha256": digest,
    }


def write_csv(path: Path, fieldnames: List[str], records: Iterable[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(
            "/data1/liuyeqiang/nas/A100/codex_archive_20261014/TempRMOT/exps/default_rk_v2"
        ),
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=Path("/data1/liuyeqiang/RMOT_JEV_DIAG_20261021/analysis"),
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=40,
        help="Bound the number of expression pairs opened on a remote NAS mount.",
    )
    parser.add_argument(
        "--hash-files",
        action="store_true",
        help="Compute SHA256 for sampled files; this is slow over SSHFS.",
    )
    parser.add_argument(
        "--per-video-records",
        type=int,
        default=10,
        help="Maximum number of expression pairs sampled from each video.",
    )
    args = parser.parse_args()
    result_root = args.root / "results_epoch2"
    if not result_root.is_dir():
        raise SystemExit(f"missing result root: {result_root}")

    inventory = []
    video_summary = []
    representative = []
    processed = 0
    for video_dir in sorted(path for path in result_root.iterdir() if path.is_dir()):
        expression_dirs = sorted(path for path in video_dir.iterdir() if path.is_dir())
        video_records = []
        for expression_dir in expression_dirs:
            if processed >= args.max_records or len(video_records) >= args.per_video_records:
                break
            gt = expression_dir / "gt.txt"
            prediction = expression_dir / "predict.txt"
            if not (gt.is_file() and prediction.is_file()):
                continue
            gt_stats = file_stats(gt, args.hash_files)
            pred_stats = file_stats(prediction, args.hash_files)
            processed += 1
            record = {
                "dataset": "Refer-KITTI-V2",
                "protocol": "legacy-TempRMOT-results_epoch2",
                "status": "AUXILIARY_NOT_COMPARABLE",
                "video": video_dir.name,
                "expression": expression_dir.name,
                "candidate_source": "unknown; archived TempRMOT final result tree",
                "checkpoint": "not recorded in this result directory",
                "gt_path": str(gt),
                "predict_path": str(prediction),
                "gt_rows": gt_stats["rows"],
                "pred_rows": pred_stats["rows"],
                "gt_frames": gt_stats["frames"],
                "pred_frames": pred_stats["frames"],
                "gt_ids": gt_stats["ids"],
                "pred_ids": pred_stats["ids"],
                "gt_min_frame": gt_stats["min_frame"],
                "gt_max_frame": gt_stats["max_frame"],
                "pred_min_frame": pred_stats["min_frame"],
                "pred_max_frame": pred_stats["max_frame"],
                "gt_columns": gt_stats["column_shapes"],
                "pred_columns": pred_stats["column_shapes"],
                "gt_bad_rows": gt_stats["bad_rows"],
                "pred_bad_rows": pred_stats["bad_rows"],
                "gt_sha256": gt_stats["sha256"],
                "pred_sha256": pred_stats["sha256"],
            }
            inventory.append(record)
            video_records.append(record)
            if len(representative) < 12:
                representative.append(record)
        if video_records:
            video_summary.append(
                {
                    "dataset": "Refer-KITTI-V2",
                    "protocol": "legacy-TempRMOT-results_epoch2",
                    "status": "AUXILIARY_NOT_COMPARABLE",
                    "video": video_dir.name,
                    "expression_count": len(video_records),
                    "expression_dirs_seen": len(expression_dirs),
                    "sampled": len(video_records) < len(expression_dirs),
                    "gt_files": len(video_records),
                    "predict_files": len(video_records),
                    "gt_rows": sum(int(row["gt_rows"]) for row in video_records),
                    "pred_rows": sum(int(row["pred_rows"]) for row in video_records),
                }
            )

    fields = list(inventory[0].keys()) if inventory else [
        "dataset", "protocol", "status", "video", "expression", "candidate_source",
        "checkpoint", "gt_path", "predict_path", "gt_rows", "pred_rows", "gt_frames",
        "pred_frames", "gt_ids", "pred_ids", "gt_min_frame", "gt_max_frame",
        "pred_min_frame", "pred_max_frame", "gt_columns", "pred_columns", "gt_bad_rows",
        "pred_bad_rows", "gt_sha256", "pred_sha256",
    ]
    write_csv(args.out_root / "legacy_temprmot_v2_inventory.csv", fields, inventory)
    write_csv(
        args.out_root / "legacy_temprmot_v2_video_summary.csv",
        [
            "dataset", "protocol", "status", "video", "expression_count", "gt_files",
            "predict_files", "gt_rows", "pred_rows",
        ],
        video_summary,
    )
    (args.out_root / "legacy_temprmot_v2_representative.json").write_text(
        json.dumps(
            {
                "status": "AUXILIARY_NOT_COMPARABLE",
                "reason": (
                    "This is an archived TempRMOT output tree. It is not the official "
                    "YesTrack/FlexHook candidate protocol and has no verified raw candidate set."
                ),
                "cases": representative,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"result_root": str(result_root), "records": len(inventory), "videos": video_summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()
