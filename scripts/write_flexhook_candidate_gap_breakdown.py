#!/usr/bin/env python3
"""Write the reproducible candidate-gap summary used by the report.

The source tables are produced by the independent candidate ceiling and error
scripts.  This summary deliberately reports coverage gaps and tracker-ID
proxies only; it does not turn them into HOTA/IDF1 or completed FlexHook
oracle results.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def find_row(rows: list[dict[str, str]], **criteria: str) -> dict[str, str]:
    for row in rows:
        if all(row.get(key) == value for key, value in criteria.items()):
            return row
    raise ValueError(f"missing row: {criteria}")


def add_row(
    output: list[dict[str, str]],
    scope: str,
    threshold: str,
    metric: str,
    numerator: int,
    denominator: int,
    rate: float,
    unit: str,
    interpretation: str,
) -> None:
    output.append(
        {
            "scope": scope,
            "threshold": threshold,
            "metric": metric,
            "numerator": str(numerator),
            "denominator": str(denominator),
            "rate": f"{rate:.10f}",
            "unit": unit,
            "interpretation": interpretation,
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ceiling",
        type=Path,
        default=Path("analysis/flexhook_candidate_ceiling.csv"),
    )
    parser.add_argument(
        "--errors",
        type=Path,
        default=Path("analysis/flexhook_candidate_error_summary.csv"),
    )
    parser.add_argument(
        "--identity",
        type=Path,
        default=Path("analysis/flexhook_identity_proxy.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("analysis/flexhook_candidate_gap_breakdown.csv"),
    )
    args = parser.parse_args()

    ceiling = read_csv(args.ceiling)
    errors = read_csv(args.errors)
    identity = read_csv(args.identity)

    aggregate = {
        float(row["iou_threshold"]): row
        for row in ceiling
        if row["scope"] == "aggregate"
    }
    required_thresholds = {0.3, 0.5, 0.7}
    if set(aggregate) != required_thresholds:
        raise ValueError(f"unexpected aggregate thresholds: {sorted(aggregate)}")

    total = int(aggregate[0.5]["gt_boxes"])
    output: list[dict[str, str]] = []
    for threshold in (0.3, 0.5, 0.7):
        row = aggregate[threshold]
        matched = int(row["matched_boxes"])
        label = f"iou>={threshold:.2f}"
        add_row(
            output,
            "aggregate",
            label,
            "matched_gt_boxes",
            matched,
            total,
            matched / total,
            "fraction",
            "GT boxes covered by at least one official candidate under one-to-one frame matching.",
        )
        add_row(
            output,
            "aggregate",
            label,
            "unmatched_gt_boxes",
            total - matched,
            total,
            (total - matched) / total,
            "fraction",
            "Candidate-level ceiling gap; selection or identity decisions cannot create these boxes.",
        )

    add_row(
        output,
        "threshold_gap",
        "iou0.30_to_0.50",
        "coverage_drop_boxes",
        int(aggregate[0.3]["matched_boxes"]) - int(aggregate[0.5]["matched_boxes"]),
        total,
        (int(aggregate[0.3]["matched_boxes"]) - int(aggregate[0.5]["matched_boxes"])) / total,
        "fraction",
        "Additional coverage lost when requiring tighter box overlap; a geometry/precision warning, not a model selection event.",
    )
    add_row(
        output,
        "threshold_gap",
        "iou0.50_to_0.70",
        "coverage_drop_boxes",
        int(aggregate[0.5]["matched_boxes"]) - int(aggregate[0.7]["matched_boxes"]),
        total,
        (int(aggregate[0.5]["matched_boxes"]) - int(aggregate[0.7]["matched_boxes"])) / total,
        "fraction",
        "Additional coverage lost at high overlap quality; a geometry/precision warning, not a model selection event.",
    )

    video_0019 = find_row(errors, video="0019")
    global_missing = total - int(aggregate[0.5]["matched_boxes"])
    missing_0019 = int(video_0019["missing_boxes"])
    add_row(
        output,
        "0019",
        "iou>=0.50",
        "share_of_global_missing_boxes",
        missing_0019,
        global_missing,
        missing_0019 / global_missing,
        "fraction",
        "Share of all IoU 0.5 candidate misses contributed by video 0019.",
    )

    identity_05 = find_row(identity, iou_threshold="0.5")
    target_tracks = int(identity_05["target_tracks"])
    matched_tracks = int(identity_05["tracks_with_any_match"])
    switched_tracks = int(identity_05["tracks_with_switch"])
    add_row(
        output,
        "aggregate",
        "iou>=0.50",
        "target_tracks_without_any_candidate_match",
        target_tracks - matched_tracks,
        target_tracks,
        (target_tracks - matched_tracks) / target_tracks,
        "fraction",
        "Target trajectories with no candidate match at any frame; not repairable by selection.",
    )
    add_row(
        output,
        "aggregate",
        "iou>=0.50",
        "target_tracks_with_candidate_id_switch",
        switched_tracks,
        target_tracks,
        switched_tracks / target_tracks,
        "fraction",
        "Target trajectories whose matched candidate IDs switch; candidate identity proxy, not official IDF1.",
    )
    add_row(
        output,
        "aggregate",
        "iou>=0.50",
        "candidate_id_switches_per_100_matched_frames",
        int(identity_05["id_switches"]),
        int(identity_05["matched_target_frames"]),
        100 * int(identity_05["id_switches"]) / int(identity_05["matched_target_frames"]),
        "per_100_frames",
        "Candidate ID switch proxy on matched target frames; not a completed model temporal error statistic.",
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "scope",
                "threshold",
                "metric",
                "numerator",
                "denominator",
                "rate",
                "unit",
                "interpretation",
            ],
        )
        writer.writeheader()
        writer.writerows(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
