#!/usr/bin/env python3
"""Candidate coverage, selection errors, and Oracle files for YesTrack V2.

The released ``v2best_track_result`` is the TempRMOT* candidate pool used by
YesTrack.  This script never uses model scores to build the candidate ceiling:
it matches every candidate to the released MOTC GT first, then attaches the
YesTrack confidence from ``predict_with_conf.txt`` for selection diagnostics.
O1/O2/O3 files are written for evaluation with the official YesTrack
``eval_refer_kitti_mot.py`` script.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import DefaultDict, Iterable, Optional


Row = tuple[int, int, float, float, float, float]


def read_rows(path: Path) -> list[Row]:
    rows: list[Row] = []
    if not path.is_file():
        raise FileNotFoundError(path)
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        fields = [x.strip() for x in raw.split(",")]
        if len(fields) < 6:
            continue
        try:
            rows.append(
                (
                    int(float(fields[0])),
                    int(float(fields[1])),
                    float(fields[2]),
                    float(fields[3]),
                    float(fields[4]),
                    float(fields[5]),
                )
            )
        except ValueError:
            continue
    return rows


def read_scored(path: Path) -> list[tuple[Row, float]]:
    out: list[tuple[Row, float]] = []
    if not path.is_file():
        raise FileNotFoundError(path)
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        fields = [x.strip() for x in raw.split(",")]
        if len(fields) < 6:
            continue
        try:
            row: Row = (
                int(float(fields[0])),
                int(float(fields[1])),
                float(fields[2]),
                float(fields[3]),
                float(fields[4]),
                float(fields[5]),
            )
            score = float(fields[6]) if len(fields) >= 7 else 1.0
        except ValueError:
            continue
        out.append((row, score))
    return out


def iou(a: Row, b: Row) -> float:
    ax1, ay1, aw, ah = a[2:]
    bx1, by1, bw, bh = b[2:]
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter <= 0:
        return 0.0
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def match_one_to_one(
    gt_rows: list[Row], pred_rows: list[Row], threshold: float
) -> dict[int, tuple[int, float]]:
    """Return gt-index -> (prediction-index, IoU), greedily by IoU."""
    pairs: list[tuple[float, int, int]] = []
    for gi, gt in enumerate(gt_rows):
        for pi, pred in enumerate(pred_rows):
            overlap = iou(gt, pred)
            if overlap >= threshold:
                pairs.append((overlap, gi, pi))
    pairs.sort(reverse=True)
    used_gt: set[int] = set()
    used_pred: set[int] = set()
    out: dict[int, tuple[int, float]] = {}
    for overlap, gi, pi in pairs:
        if gi in used_gt or pi in used_pred:
            continue
        used_gt.add(gi)
        used_pred.add(pi)
        out[gi] = (pi, overlap)
    return out


def grouped(rows: Iterable[Row]) -> DefaultDict[int, list[tuple[int, Row]]]:
    out: DefaultDict[int, list[tuple[int, Row]]] = defaultdict(list)
    for idx, row in enumerate(rows):
        out[row[0]].append((idx, row))
    return out


def expression_match(gt_rows: list[Row], pred_rows: list[Row], threshold: float):
    matches: dict[int, tuple[int, float]] = {}
    gt_by_frame = grouped(gt_rows)
    pred_by_frame: DefaultDict[int, list[Row]] = defaultdict(list)
    for row in pred_rows:
        pred_by_frame[row[0]].append(row)
    for frame, gt_items in gt_by_frame.items():
        local_gt = [row for _idx, row in gt_items]
        local = match_one_to_one(local_gt, pred_by_frame.get(frame, []), threshold)
        frame_pred_indices = [
            idx for idx, row in enumerate(pred_rows) if row[0] == frame
        ]
        for local_gi, (local_pi, overlap) in local.items():
            matches[gt_items[local_gi][0]] = (frame_pred_indices[local_pi], overlap)
    return matches


def task_paths(gt_root: Path, candidate_root: Path, scored_root: Path):
    for gt_dir in sorted(p for p in gt_root.iterdir() if p.is_dir()):
        name = gt_dir.name
        if "__" not in name:
            continue
        seq, expr = name.split("__", 1)
        yield (
            seq,
            expr,
            gt_dir / "gt" / "gt.txt",
            candidate_root / seq / expr / "predict.txt",
            scored_root / seq / expr / "predict_with_conf.txt",
        )


def write_rows(path: Path, rows: Iterable[Row], ids_from_gt: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for frame, tid, x, y, w, h in rows:
            f.write(f"{frame},{tid},{x:g},{y:g},{w:g},{h:g},1.000000\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-root", type=Path, required=True)
    ap.add_argument("--scored-root", type=Path, required=True)
    ap.add_argument("--gt-root", type=Path, required=True)
    ap.add_argument("--output-root", type=Path, required=True)
    ap.add_argument("--match-iou", type=float, default=0.5)
    ap.add_argument("--decision-thresholds", type=float, nargs="+", default=[0.3, 0.5, 0.6, 0.7])
    args = ap.parse_args()

    tasks = list(task_paths(args.gt_root, args.candidate_root, args.scored_root))
    if not tasks:
        raise RuntimeError("no expression tasks found")

    aggregate = {
        str(thr): {
            "gt_boxes": 0,
            "candidate_matched_boxes": 0,
            "candidate_missing": 0,
            "matched_true_positive": 0,
            "selection_false_negative": 0,
            "selection_false_positive": 0,
            "score_rows": 0,
            "score_missing_rows": 0,
            "expressions": 0,
            "fully_covered_expressions": 0,
        }
        for thr in args.decision_thresholds
    }
    coverage = {
        str(thr): {
            "gt_boxes": 0,
            "matched_boxes": 0,
            "missing_boxes": 0,
            "expressions": 0,
            "fully_covered_expressions": 0,
            "mean_expression_recall_sum": 0.0,
        }
        for thr in [0.3, args.match_iou, 0.7]
    }
    per_video: DefaultDict[str, dict] = defaultdict(lambda: defaultdict(int))
    identity = {
        str(thr): {
            "target_tracks": 0,
            "tracks_with_any_match": 0,
            "matched_target_frames": 0,
            "target_track_frames": 0,
            "id_switches": 0,
            "tracks_with_switch": 0,
            "purity_sum": 0.0,
            "purity_tracks": 0,
        }
        for thr in [args.match_iou, 0.6]
    }

    oracle_dirs = {
        "O1": args.output_root / f"O1_iou{args.match_iou:.2f}",
        "O2": args.output_root / f"O2_iou{args.match_iou:.2f}",
        "O3": args.output_root / "O3_gt",
    }
    task_count = 0
    row_count = 0
    for seq, expr, gt_path, candidate_path, scored_path in tasks:
        gt_rows = read_rows(gt_path)
        candidate_rows = read_rows(candidate_path)
        scored_rows = read_scored(scored_path)
        if len(candidate_rows) != len(scored_rows):
            raise RuntimeError(f"row count mismatch: {seq}/{expr}: candidate={len(candidate_rows)} scored={len(scored_rows)}")
        for idx, (crow, (srow, _score)) in enumerate(zip(candidate_rows, scored_rows)):
            if crow[:2] != srow[:2]:
                raise RuntimeError(f"frame/id mismatch at {seq}/{expr} row {idx}: {crow[:2]} != {srow[:2]}")
        scores = [score for _row, score in scored_rows]
        row_count += len(candidate_rows)
        task_count += 1

        all_matches_by_iou = {}
        for cov_thr in coverage:
            matches = expression_match(gt_rows, candidate_rows, float(cov_thr))
            all_matches_by_iou[float(cov_thr)] = matches
            rec = len(matches) / len(gt_rows) if gt_rows else 1.0
            c = coverage[cov_thr]
            c["gt_boxes"] += len(gt_rows)
            c["matched_boxes"] += len(matches)
            c["missing_boxes"] += len(gt_rows) - len(matches)
            c["expressions"] += 1
            c["fully_covered_expressions"] += int(len(matches) == len(gt_rows))
            c["mean_expression_recall_sum"] += rec
            per_video[seq][f"gt_boxes@{cov_thr}"] += len(gt_rows)
            per_video[seq][f"matched@{cov_thr}"] += len(matches)

        oracle_matches = all_matches_by_iou[float(args.match_iou)]
        selected_o1: list[Row] = []
        selected_o2: list[Row] = []
        for gi, (pi, _overlap) in oracle_matches.items():
            selected_o1.append(candidate_rows[pi])
            gt = gt_rows[gi]
            pred = candidate_rows[pi]
            selected_o2.append((gt[0], gt[1], pred[2], pred[3], pred[4], pred[5]))
        write_rows(oracle_dirs["O1"] / seq / expr / "predict_with_conf.txt", selected_o1)
        write_rows(oracle_dirs["O2"] / seq / expr / "predict_with_conf.txt", selected_o2)
        write_rows(oracle_dirs["O3"] / seq / expr / "predict_with_conf.txt", gt_rows)

        for thr in args.decision_thresholds:
            key = str(thr)
            c = aggregate[key]
            selected = {idx for idx, score in enumerate(scores) if score >= float(thr)}
            matched_pred = {pi for pi, _overlap in oracle_matches.values()}
            c["gt_boxes"] += len(gt_rows)
            c["candidate_matched_boxes"] += len(oracle_matches)
            c["candidate_missing"] += len(gt_rows) - len(oracle_matches)
            c["matched_true_positive"] += sum(
                1 for _gi, (pi, _ov) in oracle_matches.items() if pi in selected
            )
            c["selection_false_negative"] += sum(
                1 for _gi, (pi, _ov) in oracle_matches.items() if pi not in selected
            )
            c["selection_false_positive"] += len(selected - matched_pred)
            c["score_rows"] += len(scores)
            c["expressions"] += 1
            c["fully_covered_expressions"] += int(
                len(gt_rows) > 0 and all(
                    pi in selected for pi, _ov in oracle_matches.values()
                ) and len(oracle_matches) == len(gt_rows)
            )

        for thr in [args.match_iou, 0.6]:
            matches = expression_match(gt_rows, candidate_rows, float(thr))
            selected = {idx for idx, score in enumerate(scores) if score >= float(thr)}
            by_track: DefaultDict[int, list[tuple[int, Optional[int]]]] = defaultdict(list)
            for gi, gt in enumerate(gt_rows):
                pi = matches.get(gi, (None, 0.0))[0]
                if pi is not None and pi in selected:
                    pred_id: Optional[int] = candidate_rows[pi][1]
                else:
                    pred_id = None
                by_track[gt[1]].append((gt[0], pred_id))
            ident = identity[str(thr)]
            for sequence in by_track.values():
                ident["target_tracks"] += 1
                ident["target_track_frames"] += len(sequence)
                matched = [(f, tid) for f, tid in sorted(sequence) if tid is not None]
                ident["matched_target_frames"] += len(matched)
                if not matched:
                    continue
                ident["tracks_with_any_match"] += 1
                counts = Counter(tid for _f, tid in matched)
                ident["purity_sum"] += max(counts.values()) / len(matched)
                ident["purity_tracks"] += 1
                switches = sum(matched[i][1] != matched[i - 1][1] for i in range(1, len(matched)))
                ident["id_switches"] += switches
                ident["tracks_with_switch"] += int(switches > 0)

    for c in coverage.values():
        c["candidate_recall"] = c["matched_boxes"] / c["gt_boxes"] if c["gt_boxes"] else 0.0
        c["missing_rate"] = c["missing_boxes"] / c["gt_boxes"] if c["gt_boxes"] else 0.0
        c["full_expression_rate"] = c["fully_covered_expressions"] / c["expressions"] if c["expressions"] else 0.0
        c["mean_expression_recall"] = c.pop("mean_expression_recall_sum") / c["expressions"] if c["expressions"] else 0.0
    for c in aggregate.values():
        c["candidate_recall"] = c["candidate_matched_boxes"] / c["gt_boxes"] if c["gt_boxes"] else 0.0
        c["selection_precision_proxy"] = c["matched_true_positive"] / (c["matched_true_positive"] + c["selection_false_positive"]) if (c["matched_true_positive"] + c["selection_false_positive"]) else 0.0
        c["selection_recall_given_candidate"] = c["matched_true_positive"] / c["candidate_matched_boxes"] if c["candidate_matched_boxes"] else 0.0
        c["full_expression_rate"] = c["fully_covered_expressions"] / c["expressions"] if c["expressions"] else 0.0
    for ident in identity.values():
        ident["matched_frame_recall"] = ident["matched_target_frames"] / ident["target_track_frames"] if ident["target_track_frames"] else 0.0
        ident["tracks_with_any_match_rate"] = ident["tracks_with_any_match"] / ident["target_tracks"] if ident["target_tracks"] else 0.0
        ident["mean_id_purity"] = ident.pop("purity_sum") / ident.pop("purity_tracks") if ident["purity_tracks"] else 0.0
        ident["switches_per_100_matched_frames"] = 100.0 * ident["id_switches"] / ident["matched_target_frames"] if ident["matched_target_frames"] else 0.0

    result = {
        "status": "COMPLETE",
        "protocol": "YesTrack V2 released TempRMOT* candidate pool matched one-to-one per frame against released MOTC GT",
        "expressions": task_count,
        "candidate_rows": row_count,
        "match_iou": args.match_iou,
        "coverage": coverage,
        "selection_errors": aggregate,
        "identity_proxy": identity,
        "per_video": per_video,
        "oracle_dirs": {k: str(v) for k, v in oracle_dirs.items()},
        "caveat": "O1/O2/O3 are offline counterfactual files; official HOTA/DetA/AssA/IDF1 must be read from eval_refer_kitti_mot.py, not inferred from these counts.",
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "yestrack_candidate_oracle_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
