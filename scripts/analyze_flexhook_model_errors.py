#!/usr/bin/env python3
"""Attribute frozen FlexHook decisions against the fixed candidate pool.

This produces compact tracked summaries rather than a multi-hundred-megabyte
per-decision ledger.  Every count is reconstructed from the official raw
``result.json`` logits, the original candidate rows, and gt_template.  GT is
used only here, after inference, for offline attribution.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from build_flexhook_oracle_results import MotRow, candidate_pool, one_to_one_matches, read_gt


def p_yes(score: list[float] | tuple[float, ...] | None) -> float | None:
    if not score or len(score) < 2:
        return None
    value = float(score[1]) - float(score[0])
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-json", type=Path, required=True)
    parser.add_argument("--track-root", type=Path, required=True)
    parser.add_argument("--gt-root", type=Path, required=True)
    parser.add_argument("--expression-root", type=Path, required=True)
    parser.add_argument("--summary-csv", type=Path, required=True)
    parser.add_argument("--events-csv", type=Path, required=True)
    parser.add_argument("--chains-csv", type=Path, required=True)
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    args = parser.parse_args()

    result = json.loads(args.result_json.read_text(encoding="utf-8"))
    videos = sorted(result)
    summary_counts: dict[tuple[str, str], dict[str, object]] = {}
    chain_rows: list[dict[str, object]] = []

    def bucket(video: str, error_type: str) -> dict[str, object]:
        key = (video, error_type)
        if key not in summary_counts:
            summary_counts[key] = {
                "video": video,
                "error_type": error_type,
                "event_count": 0,
                "gt_frame_count": 0,
                "positive_decision_count": 0,
                "negative_decision_count": 0,
                "p_yes_sum": 0.0,
                "p_yes_count": 0,
            }
        return summary_counts[key]

    for video in videos:
        candidates = candidate_pool(args.track_root, video)
        expression_sentences = {
            path.stem: json.loads(path.read_text(encoding="utf-8"))["sentence"]
            for path in sorted((args.expression_root / video).glob("*.json"))
        }

        # Invert the raw result once per video.  This avoids scanning every
        # object/frame for every expression during false-positive counting.
        entries_by_sentence: dict[str, list[tuple[int, int, list[float]]]] = defaultdict(list)
        for object_id, frame_dict in result[video].items():
            object_id_int = int(object_id)
            for frame_key, score_dict in frame_dict.items():
                frame0 = int(frame_key)
                for sentence, score in score_dict.items():
                    entries_by_sentence[sentence].append((frame0, object_id_int, score))

        for expression, sentence in expression_sentences.items():
            gt_rows = read_gt(args.gt_root / video / expression / "gt.txt")
            by_frame: dict[int, list[tuple[int, MotRow]]] = defaultdict(list)
            for index, row in enumerate(gt_rows):
                by_frame[row.frame].append((index, row))

            matched_gt: dict[int, tuple[MotRow, float]] = {}
            matched_candidate_keys: set[tuple[int, int]] = set()
            status_by_track: dict[int, list[tuple[int, str]]] = defaultdict(list)
            for frame, indexed_gt in by_frame.items():
                local_matches = one_to_one_matches(
                    [row for _, row in indexed_gt], candidates.get(frame, []), args.iou_threshold
                )
                for local_index, match in local_matches.items():
                    gt_index = indexed_gt[local_index][0]
                    matched_gt[gt_index] = match
                    matched_candidate_keys.add((frame - 1, match[0].track_id))

            for gt_index, gt_row in enumerate(gt_rows):
                match = matched_gt.get(gt_index)
                if match is None:
                    error_type = "CANDIDATE_MISSING"
                    current = bucket(video, error_type)
                    current["event_count"] = int(current["event_count"]) + 1
                    current["gt_frame_count"] = int(current["gt_frame_count"]) + 1
                    status_by_track[gt_row.track_id].append((gt_row.frame, error_type))
                    continue

                candidate = match[0]
                score = (
                    result[video]
                    .get(str(candidate.track_id), {})
                    .get(str(candidate.frame - 1), {})
                    .get(sentence)
                )
                if score is None:
                    error_type = "MODEL_WINDOW_MISSING"
                    current = bucket(video, error_type)
                    current["event_count"] = int(current["event_count"]) + 1
                    current["gt_frame_count"] = int(current["gt_frame_count"]) + 1
                    status_by_track[gt_row.track_id].append((gt_row.frame, error_type))
                    continue

                probability = p_yes(score)
                positive = len(score) > 1 and max(range(len(score)), key=lambda index: score[index]) > 0
                error_type = "MATCHED_TRUE_POSITIVE" if positive else "REFER_FALSE_NEGATIVE"
                current = bucket(video, error_type)
                current["event_count"] = int(current["event_count"]) + 1
                current["gt_frame_count"] = int(current["gt_frame_count"]) + 1
                current["positive_decision_count"] = int(current["positive_decision_count"]) + int(positive)
                current["negative_decision_count"] = int(current["negative_decision_count"]) + int(not positive)
                if probability is not None:
                    current["p_yes_sum"] = float(current["p_yes_sum"]) + probability
                    current["p_yes_count"] = int(current["p_yes_count"]) + 1
                status_by_track[gt_row.track_id].append((gt_row.frame, error_type))

            false_positive = bucket(video, "REFER_FALSE_POSITIVE")
            for frame0, candidate_id, score in entries_by_sentence.get(sentence, []):
                positive = len(score) > 1 and max(range(len(score)), key=lambda index: score[index]) > 0
                if not positive or (frame0, candidate_id) in matched_candidate_keys:
                    continue
                false_positive["event_count"] = int(false_positive["event_count"]) + 1
                probability = p_yes(score)
                if probability is not None:
                    false_positive["p_yes_sum"] = float(false_positive["p_yes_sum"]) + probability
                    false_positive["p_yes_count"] = int(false_positive["p_yes_count"]) + 1

            # Contiguous runs are descriptive chains only.  They do not prove
            # TCP/TRP causality, so the status records that limitation.
            for track_id, sequence in status_by_track.items():
                sequence.sort()
                start = 0
                while start < len(sequence):
                    error_type = sequence[start][1]
                    end = start
                    while (
                        end + 1 < len(sequence)
                        and sequence[end + 1][1] == error_type
                        and sequence[end + 1][0] == sequence[end][0] + 1
                    ):
                        end += 1
                    duration = end - start + 1
                    if duration >= 2 and error_type in {"CANDIDATE_MISSING", "REFER_FALSE_NEGATIVE"}:
                        chain_rows.append(
                            {
                                "method": "FlexHook",
                                "dataset": "Refer-KITTI-V2",
                                "protocol": "official-v2",
                                "sequence": video,
                                "expression": expression,
                                "track_id": track_id,
                                "error_type": error_type + "_CHAIN",
                                "start_frame": sequence[start][0],
                                "end_frame": sequence[end][0],
                                "duration": duration,
                                "first_cause": error_type,
                                "propagation_status": "DESCRIPTIVE_NOT_CAUSAL_TCP_TRP_PROOF",
                                "notes": "Consecutive GT-frame labels from frozen candidate/raw-score attribution.",
                            }
                        )
                    start = end + 1

    total_gt_by_video: Counter[str] = Counter()
    for video in videos:
        for path in (args.gt_root / video).glob("*/gt.txt"):
            total_gt_by_video[video] += len(read_gt(path))

    summary_rows: list[dict[str, object]] = []
    event_rows: list[dict[str, object]] = []
    for (video, error_type), values in sorted(summary_counts.items()):
        event_count = int(values["event_count"])
        mean_probability = (
            float(values["p_yes_sum"]) / int(values["p_yes_count"])
            if int(values["p_yes_count"])
            else None
        )
        row = {
            "method": "FlexHook",
            "dataset": "Refer-KITTI-V2",
            "protocol": "official-v2",
            "video": video,
            "error_type": error_type,
            "event_count": event_count,
            "gt_frame_count": int(values["gt_frame_count"]),
            "gt_frame_share": (
                int(values["gt_frame_count"]) / total_gt_by_video[video]
                if total_gt_by_video[video]
                else ""
            ),
            "mean_p_yes": "" if mean_probability is None else mean_probability,
            "notes": "GT is used only for offline attribution; matched true positives are included for denominator audit.",
        }
        summary_rows.append(row)
        event_rows.append(
            {
                "method": "FlexHook",
                "dataset": "Refer-KITTI-V2",
                "protocol": "official-v2",
                "sequence": video,
                "expression": "*",
                "frame": "aggregate",
                "track_id": "*",
                "error_type": error_type,
                "source_stage": (
                    "stage1_candidate" if error_type == "CANDIDATE_MISSING" else
                    "stage2_selection" if error_type.startswith("REFER_") else
                    "official_test_window" if error_type == "MODEL_WINDOW_MISSING" else "audit"
                ),
                "status": "AGGREGATED_FROM_RAW_LOGITS",
                "confidence_raw": "" if mean_probability is None else mean_probability,
                "confidence_final": "",
                "notes": "Compact aggregate; raw result.json is retained in the ignored run receipt.",
            }
        )

    write_csv(
        args.summary_csv,
        ["method", "dataset", "protocol", "video", "error_type", "event_count", "gt_frame_count", "gt_frame_share", "mean_p_yes", "notes"],
        summary_rows,
    )
    write_csv(
        args.events_csv,
        ["method", "dataset", "protocol", "sequence", "expression", "frame", "track_id", "error_type", "source_stage", "status", "confidence_raw", "confidence_final", "notes"],
        event_rows,
    )
    write_csv(
        args.chains_csv,
        ["method", "dataset", "protocol", "sequence", "expression", "track_id", "error_type", "start_frame", "end_frame", "duration", "first_cause", "propagation_status", "notes"],
        chain_rows,
    )
    print(json.dumps({"summary_rows": len(summary_rows), "event_rows": len(event_rows), "chain_rows": len(chain_rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
