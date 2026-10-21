#!/usr/bin/env python3
"""Measure the candidate-only ceiling for the official FlexHook test tuple.

This is deliberately independent of the unfinished FlexHook model run.  It
matches each expression's GT boxes in gt_template against the union of the
car and pedestrian tracker predictions, one-to-one within each frame.  The
result is a candidate coverage ceiling, not official HOTA/IDF1 and not an
O0/O1/O2 replacement.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import DefaultDict, Iterable, Mapping, Sequence


Row = tuple[int, int, float, float, float, float]


def read_mot(path: Path) -> list[Row]:
    rows: list[Row] = []
    if not path.is_file() or path.stat().st_size == 0:
        return rows
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        fields = [field.strip() for field in raw.split(",")]
        if len(fields) < 6:
            continue
        try:
            frame = int(float(fields[0]))
            track_id = int(float(fields[1]))
            x, y, width, height = (float(value) for value in fields[2:6])
        except ValueError:
            continue
        rows.append((frame, track_id, x, y, width, height))
    return rows


def as_xyxy(row: Row) -> tuple[float, float, float, float]:
    _, _, x, y, width, height = row
    return x, y, x + width, y + height


def iou(left: Row, right: Row) -> float:
    lx1, ly1, lx2, ly2 = as_xyxy(left)
    rx1, ry1, rx2, ry2 = as_xyxy(right)
    ix1, iy1 = max(lx1, rx1), max(ly1, ry1)
    ix2, iy2 = min(lx2, rx2), min(ly2, ry2)
    intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if intersection <= 0:
        return 0.0
    left_area = (lx2 - lx1) * (ly2 - ly1)
    right_area = (rx2 - rx1) * (ry2 - ry1)
    union = left_area + right_area - intersection
    return intersection / union if union > 0 else 0.0


def one_to_one_matches(
    ground_truth: Sequence[Row], predictions: Sequence[Row], threshold: float
) -> dict[int, tuple[Row, float]]:
    pairs: list[tuple[float, int, int]] = []
    for gt_index, gt_row in enumerate(ground_truth):
        for prediction_index, prediction_row in enumerate(predictions):
            overlap = iou(gt_row, prediction_row)
            if overlap >= threshold:
                pairs.append((overlap, gt_index, prediction_index))
    pairs.sort(reverse=True)
    used_gt: set[int] = set()
    used_predictions: set[int] = set()
    matched: dict[int, tuple[Row, float]] = {}
    for overlap, gt_index, prediction_index in pairs:
        if gt_index in used_gt or prediction_index in used_predictions:
            continue
        used_gt.add(gt_index)
        used_predictions.add(prediction_index)
        matched[gt_index] = (predictions[prediction_index], overlap)
    return matched


def empty_metric() -> dict[str, float | int]:
    return {
        "gt_boxes": 0,
        "matched_boxes": 0,
        "candidate_recall": 0.0,
        "expressions": 0,
        "fully_covered_expressions": 0,
        "full_expression_rate": 0.0,
        "mean_expression_recall": 0.0,
        "expressions_with_any_miss": 0,
    }


def finish_metric(metric: dict[str, float | int], expression_recalls: list[float]) -> None:
    gt_boxes = int(metric["gt_boxes"])
    matched_boxes = int(metric["matched_boxes"])
    expressions = int(metric["expressions"])
    metric["candidate_recall"] = matched_boxes / gt_boxes if gt_boxes else 0.0
    metric["full_expression_rate"] = (
        int(metric["fully_covered_expressions"]) / expressions if expressions else 0.0
    )
    metric["mean_expression_recall"] = (
        sum(expression_recalls) / len(expression_recalls) if expression_recalls else 0.0
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--track-root", type=Path, required=True)
    parser.add_argument("--gt-root", type=Path, required=True)
    parser.add_argument("--videos", nargs="+", default=["0005", "0011", "0013", "0019"])
    parser.add_argument(
        "--include-pedestrian",
        action="store_true",
        help="Also include pedestrian predictions; default is the Refer-KITTI-V2 test label class 0 (car) only.",
    )
    args = parser.parse_args()

    thresholds = (0.3, 0.5, 0.7)
    predictions_by_video: dict[str, DefaultDict[int, list[Row]]] = {}
    prediction_counts: dict[str, int] = {}
    for video in args.videos:
        car = read_mot(args.track_root / video / "car" / "predict.txt")
        pedestrian = read_mot(args.track_root / video / "pedestrian" / "predict.txt")
        if not args.include_pedestrian:
            pedestrian = []
        max_car_id = max((row[1] for row in car), default=0)
        # FlexHook applies the same offset when it concatenates the two classes.
        pedestrian = [
            # FlexHook uses the maximum car ID itself as the pedestrian offset;
            # the first pedestrian ID is therefore max_car_id+1 when IDs start
            # at one, without adding a second +1 here.
            (frame, track_id + max_car_id, x, y, width, height)
            for frame, track_id, x, y, width, height in pedestrian
        ]
        by_frame: DefaultDict[int, list[Row]] = defaultdict(list)
        for row in car + pedestrian:
            by_frame[row[0]].append(row)
        predictions_by_video[video] = by_frame
        prediction_counts[video] = len(car) + len(pedestrian)

    aggregate = {str(t): empty_metric() for t in thresholds}
    per_video = {
        video: {str(t): empty_metric() for t in thresholds} for video in args.videos
    }
    expression_recalls: dict[str, list[float]] = {str(t): [] for t in thresholds}
    per_video_expression_recalls: dict[str, dict[str, list[float]]] = {
        video: {str(t): [] for t in thresholds} for video in args.videos
    }
    identity = {
        str(t): {
            "target_tracks": 0,
            "tracks_with_any_match": 0,
            "matched_target_frames": 0,
            "target_track_frames": 0,
            "mean_id_purity": 0.0,
            "id_switches": 0,
            "tracks_with_switch": 0,
        }
        for t in thresholds
    }
    purity_values: dict[str, list[float]] = {str(t): [] for t in thresholds}

    gt_file_count = 0
    for video in args.videos:
        video_gt_files = sorted((args.gt_root / video).glob("*/gt.txt"))
        gt_file_count += len(video_gt_files)
        for gt_path in video_gt_files:
            gt_rows = read_mot(gt_path)
            for threshold in thresholds:
                key = str(threshold)
                matches: dict[int, tuple[Row, float]] = {}
                by_frame: DefaultDict[int, list[tuple[int, Row]]] = defaultdict(list)
                for gt_index, row in enumerate(gt_rows):
                    by_frame[row[0]].append((gt_index, row))
                for frame, indexed_gt in by_frame.items():
                    frame_matches = one_to_one_matches(
                        [row for _, row in indexed_gt],
                        predictions_by_video[video].get(frame, []),
                        threshold,
                    )
                    for local_index, match in frame_matches.items():
                        matches[indexed_gt[local_index][0]] = match

                metric = aggregate[key]
                video_metric = per_video[video][key]
                metric["gt_boxes"] += len(gt_rows)
                metric["matched_boxes"] += len(matches)
                metric["expressions"] += 1
                video_metric["gt_boxes"] += len(gt_rows)
                video_metric["matched_boxes"] += len(matches)
                video_metric["expressions"] += 1
                expression_recall = len(matches) / len(gt_rows) if gt_rows else 1.0
                expression_recalls[key].append(expression_recall)
                per_video_expression_recalls[video][key].append(expression_recall)
                is_full = len(matches) == len(gt_rows)
                metric["fully_covered_expressions"] += int(is_full)
                metric["expressions_with_any_miss"] += int(not is_full)
                video_metric["fully_covered_expressions"] += int(is_full)
                video_metric["expressions_with_any_miss"] += int(not is_full)

                target_frames: DefaultDict[int, list[tuple[int, int | None]]] = defaultdict(list)
                for gt_index, gt_row in enumerate(gt_rows):
                    prediction = matches.get(gt_index)
                    target_frames[gt_row[1]].append(
                        (gt_row[0], prediction[0][1] if prediction else None)
                    )
                for sequence in target_frames.values():
                    identity[key]["target_tracks"] += 1
                    identity[key]["target_track_frames"] += len(sequence)
                    matched_sequence = [
                        (frame, track_id)
                        for frame, track_id in sorted(sequence)
                        if track_id is not None
                    ]
                    identity[key]["matched_target_frames"] += len(matched_sequence)
                    if not matched_sequence:
                        continue
                    identity[key]["tracks_with_any_match"] += 1
                    counts = Counter(track_id for _, track_id in matched_sequence)
                    purity = max(counts.values()) / len(matched_sequence)
                    purity_values[key].append(purity)
                    switches = sum(
                        matched_sequence[index][1] != matched_sequence[index - 1][1]
                        for index in range(1, len(matched_sequence))
                    )
                    identity[key]["id_switches"] += switches
                    identity[key]["tracks_with_switch"] += int(switches > 0)

    for threshold in thresholds:
        key = str(threshold)
        finish_metric(aggregate[key], expression_recalls[key])
        for video in args.videos:
            finish_metric(per_video[video][key], per_video_expression_recalls[video][key])
        identity[key]["matched_frame_recall"] = (
            identity[key]["matched_target_frames"] / identity[key]["target_track_frames"]
            if identity[key]["target_track_frames"]
            else 0.0
        )
        identity[key]["tracks_with_any_match_rate"] = (
            identity[key]["tracks_with_any_match"] / identity[key]["target_tracks"]
            if identity[key]["target_tracks"]
            else 0.0
        )
        identity[key]["mean_id_purity"] = (
            sum(purity_values[key]) / len(purity_values[key]) if purity_values[key] else 0.0
        )
        identity[key]["switches_per_100_matched_frames"] = (
            100 * identity[key]["id_switches"] / identity[key]["matched_target_frames"]
            if identity[key]["matched_target_frames"]
            else 0.0
        )

    result = {
        "status": "CANDIDATE_CEILING_COMPUTED",
        "protocol": (
            "FlexHook gt_template vs car predict.txt, one-to-one per frame"
            if not args.include_pedestrian
            else "FlexHook gt_template vs union(car,pedestrian predict.txt), one-to-one per frame"
        ),
        "videos": args.videos,
        "gt_file_count": gt_file_count,
        "prediction_rows_by_video": prediction_counts,
        "aggregate": aggregate,
        "per_video": per_video,
        "identity_proxy": identity,
        "caveat": "These are candidate coverage and tracker-ID diagnostics, not official HOTA/IDF1 and not the unfinished FlexHook O0/O1/O2 run.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
