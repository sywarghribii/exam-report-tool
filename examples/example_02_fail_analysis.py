"""
Example 02 — Smart fail analysis & clustering
=============================================

Parse one or more reports, then:
  * print a cross-report failure overview,
  * list the most failure-heavy group paths,
  * cluster failing subtests by signature (identical patterns), and
  * cluster them by fuzzy similarity (near-duplicates).

Run:
    python examples/example_02_fail_analysis.py sample_data/*.xml
"""

from __future__ import annotations

import glob
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from exam_toolkit import (
    cluster_by_signature,
    cluster_by_similarity,
    failure_overview,
    parse_reports,
    top_failing_groups,
)


def main() -> None:
    args = sys.argv[1:] or ["sample_data/sample_report_1.xml", "sample_data/sample_report_2.xml"]
    # expand any globs the shell didn't
    paths = [p for a in args for p in (glob.glob(a) or [a])]
    reports = list(parse_reports(paths).values())

    print("=== Failure overview ===")
    for k, v in failure_overview(reports).items():
        print(f"  {k:24s}: {v}")

    print("\n=== Top failing groups ===")
    for group, count in top_failing_groups(reports, limit=10):
        print(f"  {count:3d}  {group}")

    print("\n=== Signature clusters (identical fail patterns) ===")
    for rank, c in enumerate(cluster_by_signature(reports)[:10], 1):
        print(f"  #{rank:<2} x{c.size:<3} ({len(c.affected_test_cases)} tests)  {c.signature[:80]}")

    print("\n=== Similarity clusters (near-duplicate messages, threshold=0.82) ===")
    for rank, c in enumerate(cluster_by_similarity(reports, threshold=0.82)[:10], 1):
        print(f"  #{rank:<2} x{c.size:<3}  {c.example()[:80]}")


if __name__ == "__main__":
    main()
