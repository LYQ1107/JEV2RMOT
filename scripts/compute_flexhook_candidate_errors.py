#!/usr/bin/env python3
"""Break down candidate-only misses and tracker-ID switches for FlexHook."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import DefaultDict

from compute_flexhook_candidate_ceiling import Row, one_to_one_matches, read_mot


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--track-root", type=Path, required=True)
    parser.add_argument("--gt-root", type=Path, required=True)
    parser.add_argument("--videos", nargs="+", default=["0005", "0011", "0013", "0019"])
    args = parser.parse_args()

    threshold = 0.5
    predictions: dict[str, DefaultDict[int, list[Row]]] = {}
    prediction_rows: dict[str, int] = {}
    for video in args.videos:
        car = read_mot(args.track_root / video / "car" / "predict.txt")
        pedestrian = read_mot(args.track_root / video / "pedestrian" / "predict.txt")
        max_car_id = max((row[1] for row in car), default=0)
        pedestrian = [
            (frame, track_id + max_car_id + 1, x, y, width, height)
            for frame, track_id, x, y, width, height in pedestrian
        ]
        by_frame: DefaultDict[int, list[Row]] = defaultdict(list)
        for row in car + pedestrian:
            by_frame[row[0]].append(row)
        predictions[video] = by_frame
        prediction_rows[video] = len(car) + len(pedestrian)

    video_summary: dict[str, dict[str, int | float]] = {
        video: {
            "candidate_rows": prediction_rows[video],
            "expressions": 0,
            "gt_boxes": 0,
            "matched_boxes": 0,
            "missing_boxes": 0,
            "target_tracks": 0,
            "tracks_with_any_match": 0,
            "tracks_with_switch": 0,
            "id_switches": 0,
            "matched_target_frames": 0,
            "longest_missing_run": 0,
        }
        for video in args.videos
    }
    expression_rows: list[dict[str, int | float | str]] = []

    for video in args.videos:
        for gt_path in sorted((args.gt_root / video).glob("*/gt.txt")):
            gt_rows = read_mot(gt_path)
            indexed_by_frame: DefaultDict[int, list[tuple[int, Row]]] = defaultdict(list)
            for gt_index, row in enumerate(gt_rows):
                indexed_by_frame[row[0]].append((gt_index, row))
            matches: dict[int, tuple[Row, float]] = {}
            for frame, indexed_gt in indexed_by_frame.items():
                frame_matches = one_to_one_matches(
                    [row for _, row in indexed_gt],
                    predictions[video].get(frame, []),
                    threshold,
                )
                for local_index, match in frame_matches.items():
                    matches[indexed_gt[local_index][0]] = match

            tracks: DefaultDict[int, list[tuple[int, int | None]]] = defaultdict(list)
            for gt_index, row in enumerate(gt_rows):
                prediction = matches.get(gt_index)
                tracks[row[1]].append((row[0], prediction[0][1] if prediction else None))

            track_switches = 0
            tracks_with_switch = 0
            tracks_with_any_match = 0
            matched_target_frames = len(matches)
            longest_missing_run = 0
            for sequence in tracks.values():
                sequence.sort()
                matched_sequence = [track_id for _, track_id in sequence if track_id is not None]
                if matched_sequence:
                    tracks_with_any_match += 1
                    counts = Counter(matched_sequence)
                    switches = sum(
                        matched_sequence[index] != matched_sequence[index - 1]
                        for index in range(1, len(matched_sequence))
                    )
                    track_switches += switches
                    tracks_with_switch += int(switches > 0)
                current_missing = 0
                for index, (frame, track_id) in enumerate(sequence):
                    if index and frame != sequence[index - 1][0] + 1:
                        current_missing = 0
                    if track_id is None:
                        current_missing += 1
                        longest_missing_run = max(longest_missing_run, current_missing)
                    else:
                        current_missing = 0

            summary = video_summary[video]
            summary["expressions"] += 1
            summary["gt_boxes"] += len(gt_rows)
            summary["matched_boxes"] += matched_target_frames
            summary["missing_boxes"] += len(gt_rows) - matched_target_frames
            summary["target_tracks"] += len(tracks)
            summary["tracks_with_any_match"] += tracks_with_any_match
            summary["tracks_with_switch"] += tracks_with_switch
            summary["id_switches"] += track_switches
            summary["matched_target_frames"] += matched_target_frames
            summary["longest_missing_run"] = max(summary["longest_missing_run"], longest_missing_run)
            expression_rows.append(
                {
                    "video": video,
                    "expression": gt_path.parent.name,
                    "gt_boxes": len(gt_rows),
                    "matched_boxes": matched_target_frames,
                    "missing_boxes": len(gt_rows) - matched_target_frames,
                    "candidate_recall": matched_target_frames / len(gt_rows) if gt_rows else 1.0,
                    "target_tracks": len(tracks),
                    "tracks_with_any_match": tracks_with_any_match,
                    "tracks_with_switch": tracks_with_switch,
                    "id_switches": track_switches,
                    "longest_missing_run": longest_missing_run,
                }
            )

    for summary in video_summary.values():
        summary["candidate_recall"] = (
            summary["matched_boxes"] / summary["gt_boxes"] if summary["gt_boxes"] else 0.0
        )
        summary["missing_rate"] = (
            summary["missing_boxes"] / summary["gt_boxes"] if summary["gt_boxes"] else 0.0
        )
        summary["tracks_with_switch_rate"] = (
            summary["tracks_with_switch"] / summary["target_tracks"]
            if summary["target_tracks"]
            else 0.0
        )

    expression_rows.sort(
        key=lambda row: (-int(row["missing_boxes"]), float(row["candidate_recall"]), str(row["video"]), str(row["expression"]))
    )
    result = {
        "status": "CANDIDATE_ERROR_BREAKDOWN_COMPUTED",
        "iou_threshold": threshold,
        "protocol": "FlexHook gt_template vs union(car,pedestrian predict.txt), one-to-one per frame",
        "video_summary": video_summary,
        "top_20_expression_misses": expression_rows[:20],
        "caveat": "Candidate-only diagnostics; not model selection errors, official HOTA/IDF1, or completed FlexHook O0/O1/O2.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
