"""
exam_toolkit
============

A small, reusable toolkit for extracting, analysing and reporting on EXAM
test reports (the XML ``examReport`` format).

Import the helpers you need — the package is organised so that the extraction
layer has *no* heavy dependencies (only the standard library), and the
Excel/GUI layers are optional on top.

Quick start
-----------
>>> from exam_toolkit import parse_report
>>> report = parse_report("run.xml")
>>> report.summary()
{'total': 42, 'passed': 30, 'failed': 12, 'failed_subtests': 27}

>>> from exam_toolkit import cluster_by_signature
>>> for c in cluster_by_signature([report])[:5]:
...     print(c.size, c.signature)

Layers
------
* ``models``        – typed data structures (TestCase, Subtest, ExamReport…)
* ``extractor``     – parse XML → models, and models → flat rows
* ``comments``      – persistent reporting comments (sidecar JSON)
* ``analyzer``      – fail clustering + roll-up statistics
* ``reexecution``   – build re-run execution files from failures
* ``excel_export``  – formatted .xlsx output
* ``gui``           – optional tkinter front-end
"""

from __future__ import annotations

__version__ = "1.0.0"

# ---- models ----------------------------------------------------------
from .models import (  # noqa: F401
    ExamReport,
    Subtest,
    SubtestItem,
    TestCase,
    is_fail_verdict,
)

# ---- extraction ------------------------------------------------------
from .extractor import (  # noqa: F401
    DEFAULT_METADATA_LABELS,
    iter_test_cases,
    parse_report,
    parse_report_string,
    parse_reports,
    report_to_rows,
    test_case_to_row,
)

# ---- reporting comments ---------------------------------------------
from .comments import (  # noqa: F401
    Comment,
    CommentStore,
    merge_comments,
    seed_store_from_failures,
)

# ---- analysis --------------------------------------------------------
from .analyzer import (  # noqa: F401
    FailCluster,
    FailOccurrence,
    cluster_by_signature,
    cluster_by_similarity,
    clusters_to_rows,
    collect_fail_occurrences,
    failure_overview,
    normalise_signature,
    top_failing_groups,
)

# ---- re-execution ----------------------------------------------------
from .reexecution import (  # noqa: F401
    ExecutionItem,
    build_reexecution,
    select_failed,
    write_execution_csv,
    write_execution_json,
    write_execution_xml,
)

# ---- excel (imported lazily-safe: pandas/openpyxl required) ----------
try:
    from .excel_export import (  # noqa: F401
        export_files_to_excel,
        export_reports_to_excel,
    )
except ImportError:  # pandas/openpyxl not installed — extraction still works
    pass

__all__ = [
    "__version__",
    # models
    "ExamReport", "Subtest", "SubtestItem", "TestCase", "is_fail_verdict",
    # extraction
    "parse_report", "parse_report_string", "parse_reports",
    "iter_test_cases", "report_to_rows", "test_case_to_row",
    "DEFAULT_METADATA_LABELS",
    # comments
    "Comment", "CommentStore", "merge_comments", "seed_store_from_failures",
    # analysis
    "FailCluster", "FailOccurrence", "cluster_by_signature",
    "cluster_by_similarity", "clusters_to_rows", "collect_fail_occurrences",
    "failure_overview", "normalise_signature", "top_failing_groups",
    # re-execution
    "ExecutionItem", "build_reexecution", "select_failed",
    "write_execution_csv", "write_execution_json", "write_execution_xml",
    # excel
    "export_files_to_excel", "export_reports_to_excel",
]
