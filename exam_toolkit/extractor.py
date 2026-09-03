"""
extractor.py
============

The core, reusable extraction layer.  **This is the module you import in
other scripts** when you just want the data out of an EXAM report and don't
care about Excel, GUIs or analysis.

Typical use
-----------
>>> from exam_toolkit.extractor import parse_report, iter_test_cases
>>> report = parse_report("run_2026_07_15.xml")
>>> print(report.summary())
{'total': 42, 'passed': 30, 'failed': 12, 'failed_subtests': 27}
>>> for tc in report.failed():
...     print(tc.test_case_id, tc.group_path_str, tc.fail_count)

Everything is built on the plain standard-library XML parser and the typed
models in :mod:`exam_toolkit.models`, so there are no heavy dependencies.
"""

from __future__ import annotations

import pathlib
import xml.etree.ElementTree as ET
from typing import Dict, Iterable, Iterator, List, Union

from .models import ExamReport, Subtest, SubtestItem, TestCase

# Accept either a path-like object or a raw string path everywhere.
PathLike = Union[str, pathlib.Path]

# Metadata labels we surface as first-class columns.  Extend freely — any
# label present in the XML is still available via ``TestCase.metadata``.
DEFAULT_METADATA_LABELS = ("Variante", "Platform", "Projekt", "Link")


# ----------------------------------------------------------------------
# Low-level element -> model builders
# ----------------------------------------------------------------------
def _build_subtest(element: ET.Element) -> Subtest:
    """Turn one ``<subtests>`` element into a :class:`Subtest`."""
    items = [
        SubtestItem(key=it.get("key", ""), value=it.get("value", ""))
        for it in element.findall("./subtestItems")
    ]
    return Subtest(
        name=element.get("name", ""),
        initial_valuation=element.get("initialValuation", ""),
        final_valuation=element.get("finalValuation", ""),
        timestamp=element.get("timestamp", ""),
        type=element.get("type", ""),
        items=items,
    )


def _build_metadata(tc_element: ET.Element) -> Dict[str, str]:
    """Collect ``<metadata>/<metadataItem>`` pairs into a dict."""
    meta: Dict[str, str] = {}
    for md in tc_element.findall("./metadata"):
        for item in md.findall("./metadataItem"):
            label = item.get("label")
            value = item.get("value")
            if label is not None and value is not None:
                meta[label] = value
    return meta


def _build_test_case(tc_element: ET.Element, group_path: List[str]) -> TestCase:
    """Turn one ``<testCase>`` element into a fully populated :class:`TestCase`."""
    subtests = [_build_subtest(st) for st in tc_element.findall("./subtests")]
    return TestCase(
        test_case_id=tc_element.get("testCaseId", ""),
        name=tc_element.get("name", ""),
        start_time=tc_element.get("starttime", ""),
        duration=tc_element.get("duration", ""),
        initial_valuation=tc_element.get("initialValuation", ""),
        final_valuation=tc_element.get("finalValuation", ""),
        type=tc_element.get("type", ""),
        group_path=list(group_path),
        metadata=_build_metadata(tc_element),
        subtests=subtests,
    )


# ----------------------------------------------------------------------
# Recursive group walker
# ----------------------------------------------------------------------
def _collect(element: ET.Element, parent_path: List[str], cases: List[TestCase]) -> None:
    """Walk *element*, collecting test cases while tracking the group path.

    Handles arbitrarily nested ``<groups>``/``<group>`` structures and visits
    every grouping element exactly once (no double counting).
    """
    # 1) test cases that are direct children of the current element
    for tc in element.findall("./testCase"):
        cases.append(_build_test_case(tc, parent_path))

    # 2) recurse into child grouping elements, extending the path by their name
    for child in element:
        if child.tag in ("group", "groups"):
            name = child.get("name", "")
            child_path = parent_path + [name] if name else parent_path
            _collect(child, child_path, cases)


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
def parse_report(source: PathLike) -> ExamReport:
    """Parse an EXAM report file and return a typed :class:`ExamReport`.

    *source* may be a path string or :class:`pathlib.Path`.
    """
    path = pathlib.Path(source)
    tree = ET.parse(path)
    root = tree.getroot()

    cases: List[TestCase] = []
    _collect(root, [], cases)
    return ExamReport(source=str(path), test_cases=cases)


def parse_report_string(xml_text: str, source: str = "<string>") -> ExamReport:
    """Same as :func:`parse_report` but takes the XML as a string.

    Useful for unit tests, web uploads held in memory, or piping data in
    without ever touching disk.
    """
    root = ET.fromstring(xml_text)
    cases: List[TestCase] = []
    _collect(root, [], cases)
    return ExamReport(source=source, test_cases=cases)


def iter_test_cases(source: PathLike) -> Iterator[TestCase]:
    """Stream the test cases of a single report (a thin convenience wrapper)."""
    yield from parse_report(source).test_cases


def parse_reports(sources: Iterable[PathLike]) -> Dict[str, ExamReport]:
    """Parse many report files.

    Returns an ordered ``{source_path_str: ExamReport}`` mapping, which is
    exactly what the Excel exporter and multi-file analyses consume.
    """
    result: Dict[str, ExamReport] = {}
    for src in sources:
        report = parse_report(src)
        result[report.source] = report
    return result


# ----------------------------------------------------------------------
# Flat-dict adapters (for pandas / CSV / anything tabular)
# ----------------------------------------------------------------------
def test_case_to_row(
    tc: TestCase,
    metadata_labels: Iterable[str] = DEFAULT_METADATA_LABELS,
    fails_separator: str = "\n",
) -> Dict[str, str]:
    """Flatten one :class:`TestCase` into a single flat dict (one Excel row).

    Includes the aggregated **Fails** column (all failing subtests) and a
    **FailCount**, plus placeholders for the human reporting fields so the
    column layout is stable even before comments are merged in.
    """
    row: Dict[str, str] = {
        "TestCaseID": tc.test_case_id,
        "Name": tc.name,
        "StartTime": tc.start_time,
        "Duration": tc.duration,
        "InitialValuation": tc.initial_valuation,
        "FinalValuation": tc.final_valuation,
        "Type": tc.type,
        "GroupPath": tc.group_path_str,
        "FailCount": tc.fail_count,
        "Fails": tc.fails_text(separator=fails_separator),
    }
    for label in metadata_labels:
        row[label] = tc.meta(label)
    # Human-filled reporting fields (populated by the comments module).
    row["Reporting Comment"] = ""
    row["Rerun"] = ""
    return row


def report_to_rows(
    report: ExamReport,
    metadata_labels: Iterable[str] = DEFAULT_METADATA_LABELS,
    fails_separator: str = "\n",
) -> List[Dict[str, str]]:
    """Flatten a whole report into a list of row-dicts."""
    return [
        test_case_to_row(tc, metadata_labels, fails_separator)
        for tc in report.test_cases
    ]
