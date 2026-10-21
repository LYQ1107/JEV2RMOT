#!/usr/bin/env python3
"""Small, dependency-free delivery checks for the blocked/running audit."""

from __future__ import annotations

import csv
import ast
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path("/data1/liuyeqiang/RMOT_JEV_DIAG_20261021")


class DeliveryContractTest(unittest.TestCase):
    def test_required_reports_exist(self) -> None:
        report_names = [
            "00_RESOURCE_AUDIT.md",
            "01_DATASET_PROTOCOL_AUDIT.md",
            "02_OFFICIAL_REPRODUCTION.md",
            "03_MATCHED_TRACKER_COMPARISON.md",
            "04_DETAILED_ERROR_TAXONOMY.md",
            "05_ORACLE_HEADROOM.md",
            "06_TEMPORAL_AND_RELATIONAL_FAILURES.md",
            "07_JEV_RESEARCH_DECISION.md",
            "FINAL_REPORT.md",
        ]
        for name in report_names:
            self.assertTrue((ROOT / "reports" / name).is_file(), name)

    def test_required_tables_exist(self) -> None:
        table_names = [
            "metrics.csv",
            "sequence_metrics.csv",
            "expression_metrics.csv",
            "candidate_coverage.csv",
            "error_events.csv",
            "temporal_error_chains.csv",
            "oracle_results.csv",
            "a800_resource_manifest.csv",
            "flexhook_candidate_ceiling.csv",
            "flexhook_identity_proxy.csv",
            "flexhook_candidate_error_summary.csv",
            "flexhook_top_expression_misses.csv",
            "flexhook_candidate_gap_breakdown.csv",
            "representative_cases.json",
            "entrypoint_preflight.csv",
        ]
        for name in table_names:
            self.assertTrue((ROOT / "analysis" / name).is_file(), name)

    def test_official_metrics_are_not_fabricated(self) -> None:
        with (ROOT / "analysis" / "metrics.csv").open(newline="", encoding="utf-8") as handle:
            records = list(csv.DictReader(handle))
        self.assertGreaterEqual(len(records), 2)
        for record in records:
            self.assertIn(record["status"], {"BLOCKED", "RUNNING", "PENDING", "COMPLETE"})
            for metric in ("HOTA", "DetA", "AssA", "IDF1"):
                if record["status"] == "COMPLETE":
                    self.assertNotEqual(record[metric], "", record)
                else:
                    self.assertEqual(record[metric], "")

    def test_oracle_rows_have_explicit_incomplete_status(self) -> None:
        with (ROOT / "analysis" / "oracle_results.csv").open(newline="", encoding="utf-8") as handle:
            records = list(csv.DictReader(handle))
        self.assertEqual({record["oracle"] for record in records}, {"O0", "O1", "O2", "O3"})
        self.assertTrue(all(record["status"] in {"BLOCKED", "RUNNING", "PENDING", "COMPLETE"} for record in records))
        for record in records:
            for metric in ("HOTA", "DetA", "AssA", "IDF1", "delta_hota_vs_o0"):
                if record["status"] == "COMPLETE" and metric != "delta_hota_vs_o0":
                    self.assertNotEqual(record[metric], "", record)
                elif record["status"] != "COMPLETE":
                    self.assertEqual(record[metric], "")

    def test_no_upstream_worktree_changes(self) -> None:
        for repo in ("YesTrack", "FlexHook", "LLM2Jev"):
            output = subprocess.check_output(
                ["git", "-C", str(ROOT / "upstream" / repo), "status", "--porcelain"],
                text=True,
            )
            self.assertEqual(output.strip(), "", repo)

    def test_flexhook_source_blockers_are_reproducible(self) -> None:
        expected = {
            "SwinTransformer/utils.py": 22,
            "deit/main.py": 44,
        }
        for relative, line in expected.items():
            path = ROOT / "upstream" / "FlexHook" / relative
            with self.assertRaises(SyntaxError) as context:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            self.assertEqual(context.exception.lineno, line, relative)

    def test_case_manifest_is_honest(self) -> None:
        payload = json.loads((ROOT / "analysis" / "representative_cases.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "COMPLETE")
        self.assertEqual(payload["official_case_count"], 30)
        self.assertEqual(len(payload["cases"]), 30)
        self.assertGreaterEqual(payload["temporal_chain_case_count"], 1)
        self.assertTrue(all(Path(case["image"]).is_file() for case in payload["cases"]))

    def test_candidate_gap_summary_is_consistent(self) -> None:
        with (ROOT / "analysis" / "flexhook_candidate_gap_breakdown.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            records = list(csv.DictReader(handle))
        by_metric = {(row["scope"], row["threshold"], row["metric"]): row for row in records}
        self.assertEqual(
            by_metric[("aggregate", "iou>=0.50", "matched_gt_boxes")]["numerator"],
            "362304",
        )
        self.assertEqual(
            by_metric[("aggregate", "iou>=0.50", "unmatched_gt_boxes")]["numerator"],
            "128982",
        )
        self.assertEqual(
            by_metric[("0019", "iou>=0.50", "share_of_global_missing_boxes")]["numerator"],
            "88282",
        )


if __name__ == "__main__":
    unittest.main()
