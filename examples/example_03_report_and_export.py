"""
Example 03 — Reporting comments + Excel export
==============================================

A realistic triage workflow:
  1. Parse the reports.
  2. Seed a comment store with every failing test case (blank, ready to fill).
  3. Fill in a couple of comments (this is what a reviewer would do).
  4. Export a formatted workbook with the Fails column, the reporting
     columns filled from the store, plus Summary and Fail Analysis sheets.

Run:
    python examples/example_03_report_and_export.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from exam_toolkit import (
    CommentStore,
    export_reports_to_excel,
    parse_reports,
    seed_store_from_failures,
)

SAMPLE = pathlib.Path("sample_data")


def main() -> None:
    reports = parse_reports([SAMPLE / "sample_report_1.xml", SAMPLE / "sample_report_2.xml"])

    # 2) seed the comment store with all failures
    store = CommentStore(SAMPLE / "comments.json")
    failed_ids = [tc.test_case_id for r in reports.values() for tc in r.failed()]
    seed_store_from_failures(failed_ids, store, default_category="Untriaged")

    # 3) a reviewer fills in a few comments
    if failed_ids:
        store.set(
            failed_ids[0],
            comment="Sensor calibration drift — see JIRA-42.",
            rerun="yes",
            category="Environment",
            author="intern",
        )
    if len(failed_ids) > 1:
        store.set(
            failed_ids[1],
            comment="Known open defect, do not re-run yet.",
            rerun="no",
            category="Product defect",
            author="intern",
        )
    store.save()
    print(f"Comment store: {len(store)} entries -> {store.path}")

    # 4) export
    out = export_reports_to_excel(
        reports,
        SAMPLE / "exam_report.xlsx",
        comment_store=store,
        include_analysis=True,
        include_summary=True,
    )
    print(f"Workbook written -> {out}")


if __name__ == "__main__":
    main()
