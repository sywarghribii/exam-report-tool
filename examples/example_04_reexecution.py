"""
Example 04 — Build re-execution files
=====================================

Select the failed test cases and write re-run manifests in JSON / CSV / XML.
Also shows how to:
  * customise the selection (e.g. only one platform), and
  * override the XML template to match a real EXAM schema.

Run:
    python examples/example_04_reexecution.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from exam_toolkit import build_reexecution, parse_reports, select_failed
from exam_toolkit.reexecution import write_execution_xml

SAMPLE = pathlib.Path("sample_data")


def main() -> None:
    reports = list(parse_reports([SAMPLE / "sample_report_1.xml", SAMPLE / "sample_report_2.xml"]).values())

    # 1) default: every failed test case, all three formats
    written = build_reexecution(reports, out_dir=SAMPLE / "reexec", basename="reexec_all_failed")
    print("Default re-execution files:")
    for fmt, path in written.items():
        print(f"  {fmt:4s} -> {path}")

    # 2) custom selection: only failures on platform MLB
    items_mlb = select_failed(reports, predicate=lambda tc: tc.is_fail and tc.meta("Platform") == "MLB")
    print(f"\nMLB-only failures selected: {len(items_mlb)}")

    # 3) override the XML template to match a (hypothetical) real EXAM schema
    real_template = {
        "root_tag": "TestExecution",
        "item_tag": "Test",
        "id_attr": "id",
        "name_attr": "title",
        "group_attr": "path",
    }
    out = write_execution_xml(items_mlb, SAMPLE / "reexec" / "reexec_mlb_customschema.xml", template=real_template)
    print(f"Custom-schema XML written -> {out}")


if __name__ == "__main__":
    main()
