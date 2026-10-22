#!/usr/bin/env python3
"""Convert FlexHook's frozen MOTC candidate pool to YesTrack expression layout.

This is a format-only adapter for the shared-candidate experiment. It keeps
the original frame and bbox values and applies the same pedestrian ID offset
used by FlexHook's generate_final_results (max car ID). The resulting
per-video file is symlinked into every YesTrack expression directory; no
expression-specific filtering is performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def read_lines(path: Path) -> list[tuple[int, int, int, str]]:
    rows: list[tuple[int, int, int, str]] = []
    if not path.is_file():
        return rows
    for order, raw in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if not raw.strip():
            continue
        fields = [field.strip() for field in raw.split(",")]
        if len(fields) < 6:
            continue
        frame = int(float(fields[0]))
        track_id = int(float(fields[1]))
        rows.append((frame, track_id, order, raw.strip()))
    return rows


def rewrite_id(raw: str, track_id: int) -> str:
    fields = [field.strip() for field in raw.split(",")]
    fields[1] = str(track_id)
    return ",".join(fields)


def build_video_file(candidate_root: Path, video: str, output_root: Path) -> dict:
    car = read_lines(candidate_root / video / "car" / "predict.txt")
    ped = read_lines(candidate_root / video / "pedestrian" / "predict.txt")
    max_car_id = max((row[1] for row in car), default=0)
    merged: list[tuple[int, int, int, int, str]] = []
    for frame, track_id, order, raw in car:
        merged.append((frame, 0, order, track_id, raw))
    for frame, track_id, order, raw in ped:
        merged.append((frame, 1, order, track_id + max_car_id, rewrite_id(raw, track_id + max_car_id)))
    merged.sort(key=lambda row: (row[0], row[1], row[2]))
    output_path = output_root / video / "predict.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(row[4] for row in merged) + ("\n" if merged else ""),
        encoding="utf-8",
    )
    payload = output_path.read_bytes()
    return {
        "video": video,
        "car_rows": len(car),
        "pedestrian_rows": len(ped),
        "merged_rows": len(merged),
        "max_car_id": max_car_id,
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--flexhook-root", type=Path, required=True)
    parser.add_argument("--yestrack-candidate-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    videos = sorted(
        path.name
        for path in args.flexhook_root.iterdir()
        if path.is_dir() and (path / "car" / "predict.txt").is_file()
    )
    if not videos:
        raise RuntimeError("no FlexHook video candidate directories found")
    video_cache = args.output_root.parent / (args.output_root.name + "_video_cache")
    manifests = [build_video_file(args.flexhook_root, video, video_cache) for video in videos]

    expression_count = 0
    link_count = 0
    for video in videos:
        source = args.yestrack_candidate_root / video
        target_video = args.output_root / video
        target_video.mkdir(parents=True, exist_ok=True)
        for expr_dir in sorted(path for path in source.iterdir() if path.is_dir()):
            target_expr = target_video / expr_dir.name
            target_expr.mkdir(parents=True, exist_ok=True)
            link = target_expr / "predict.txt"
            if not link.exists():
                link.symlink_to(video_cache / video / "predict.txt")
            expression_count += 1
            link_count += 1

    result = {
        "status": "COMPLETE",
        "source": str(args.flexhook_root),
        "layout_reference": str(args.yestrack_candidate_root),
        "output_root": str(args.output_root),
        "video_cache": str(video_cache),
        "videos": videos,
        "expression_count": expression_count,
        "symlink_count": link_count,
        "video_manifests": manifests,
        "format_change": "frame/bbox preserved; pedestrian IDs offset by max car ID exactly as FlexHook",
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "shared_candidate_manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
