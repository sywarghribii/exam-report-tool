"""
Example 01 — Basic extraction
=============================

Shows how to use the toolkit as a *library* inside your own code: parse a
report, iterate test cases, read metadata, and pull the failing subtests.

Run:
    python examples/example_01_basic_extraction.py sample_data/sample_report_1.xml
(No path given -> it falls back to the bundled sample.)
"""

from __future__ import annotations

import pathlib
import sys

# Make the package importable when running the file directly from the repo.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from exam_toolkit import parse_report


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "sample_data/sample_report_1.xml"
    report = parse_report(path)

    print(f"Parsed {path}")
    print("Summary:", report.summary())
    print()

    # Iterate every test case
    for tc in report:
        verdict = "FAIL" if tc.is_fail else "pass"
        print(f"[{verdict}] {tc.test_case_id}  {tc.group_path_str}")
        print(f"        name     : {tc.name}")
        print(f"        platform : {tc.meta('Platform')}  variant: {tc.meta('Variante')}")

        # The failing subtests — this is the data behind the "Fails" column
        for st in tc.failed_subtests():
            print(f"        FAIL  -> {st.describe()}")
        # Only show the first few for a readable demo
        if int(tc.test_case_id.split('_')[-1]) >= 5:
            print("        ...")
            break


if __name__ == "__main__":
    main()
