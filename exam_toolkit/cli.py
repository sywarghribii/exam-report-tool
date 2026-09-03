"""
cli.py
======

Command-line interface, so the toolkit is usable from CI or a terminal
without the GUI.

    python -m exam_toolkit.cli export  run1.xml run2.xml -o out.xlsx
    python -m exam_toolkit.cli analyze run*.xml
    python -m exam_toolkit.cli reexec  run*.xml -d ./reexec
    python -m exam_toolkit.cli summary run*.xml
"""

from __future__ import annotations

import argparse
import glob
import sys
from typing import List

from .analyzer import cluster_by_signature, failure_overview, top_failing_groups
from .comments import CommentStore
from .excel_export import export_reports_to_excel
from .extractor import parse_reports
from .reexecution import build_reexecution


def _expand(patterns: List[str]) -> List[str]:
    return [p for pat in patterns for p in (glob.glob(pat) or [pat])]


def _cmd_summary(args) -> None:
    reports = list(parse_reports(_expand(args.inputs)).values())
    for k, v in failure_overview(reports).items():
        print(f"{k:24s}: {v}")
    print("\nTop failing groups:")
    for group, count in top_failing_groups(reports, limit=args.top):
        print(f"  {count:3d}  {group}")


def _cmd_analyze(args) -> None:
    reports = list(parse_reports(_expand(args.inputs)).values())
    for rank, c in enumerate(cluster_by_signature(reports)[: args.top], 1):
        print(f"#{rank:<2} x{c.size:<3} ({len(c.affected_test_cases)} tests)  {c.signature[:90]}")


def _cmd_export(args) -> None:
    reports = parse_reports(_expand(args.inputs))
    store = CommentStore.load(args.comments) if args.comments else None
    out = export_reports_to_excel(
        reports,
        args.output,
        comment_store=store,
        include_analysis=not args.no_analysis,
        include_summary=not args.no_summary,
    )
    print(f"Workbook written -> {out}")


def _cmd_reexec(args) -> None:
    reports = list(parse_reports(_expand(args.inputs)).values())
    written = build_reexecution(reports, out_dir=args.dir, basename=args.basename)
    for fmt, path in written.items():
        print(f"{fmt:4s} -> {path}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="exam_toolkit", description="EXAM report toolkit")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("summary", help="print failure summary + top groups")
    s.add_argument("inputs", nargs="+")
    s.add_argument("--top", type=int, default=10)
    s.set_defaults(func=_cmd_summary)

    a = sub.add_parser("analyze", help="print fail signature clusters")
    a.add_argument("inputs", nargs="+")
    a.add_argument("--top", type=int, default=20)
    a.set_defaults(func=_cmd_analyze)

    e = sub.add_parser("export", help="export a formatted Excel workbook")
    e.add_argument("inputs", nargs="+")
    e.add_argument("-o", "--output", required=True)
    e.add_argument("-c", "--comments", help="comment store JSON")
    e.add_argument("--no-analysis", action="store_true")
    e.add_argument("--no-summary", action="store_true")
    e.set_defaults(func=_cmd_export)

    r = sub.add_parser("reexec", help="build re-execution files from failures")
    r.add_argument("inputs", nargs="+")
    r.add_argument("-d", "--dir", default="./reexec")
    r.add_argument("--basename", default="reexecution")
    r.set_defaults(func=_cmd_reexec)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
