"""
reexecution.py
==============

Build "re-run these" execution files from failed test cases.

The idea: after triage you want to re-execute only the tests that failed (or
a hand-picked subset).  This module selects those test cases and writes them
out in a few interchange formats.

⚠️  About the EXAM-specific format
----------------------------------
The exact file EXAM imports to schedule a run is environment-specific (it
depends on your EXAM version and project setup).  Rather than guess a schema
and risk producing something EXAM rejects, this module:

* emits **neutral, well-structured** JSON / CSV that any scheduler can read,
  and
* provides a **template-based XML writer** (:func:`write_execution_xml`) whose
  element/attribute names you can override once you confirm the real schema
  with your team.

Swap the template, keep the selection logic — that's the design.
"""

from __future__ import annotations

import csv
import json
import pathlib
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Union
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

from .models import ExamReport, TestCase

PathLike = Union[str, pathlib.Path]


@dataclass
class ExecutionItem:
    """One test case selected for re-execution."""

    test_case_id: str
    name: str
    group_path: str
    reason: str = "final verdict FAIL"


# ----------------------------------------------------------------------
# Selection
# ----------------------------------------------------------------------
def select_failed(
    reports: Iterable[ExamReport],
    predicate: Optional[Callable[[TestCase], bool]] = None,
) -> List[ExecutionItem]:
    """Pick the test cases to re-run.

    By default selects every test case whose final verdict is a failure.
    Pass *predicate* to customise (e.g. only a certain group, or excluding
    tests already marked "won't fix" in your comment store).  Duplicate test
    case IDs across reports are de-duplicated, keeping the first seen.
    """
    if predicate is None:
        predicate = lambda tc: tc.is_fail  # noqa: E731

    seen: set = set()
    items: List[ExecutionItem] = []
    for report in reports:
        for tc in report.test_cases:
            if predicate(tc) and tc.test_case_id not in seen:
                seen.add(tc.test_case_id)
                items.append(
                    ExecutionItem(
                        test_case_id=tc.test_case_id,
                        name=tc.name,
                        group_path=tc.group_path_str,
                    )
                )
    return items


# ----------------------------------------------------------------------
# Writers
# ----------------------------------------------------------------------
def write_execution_json(items: List[ExecutionItem], path: PathLike) -> pathlib.Path:
    """Write the selection as a JSON manifest."""
    target = pathlib.Path(path)
    payload = {
        "count": len(items),
        "testCases": [vars(it) for it in items],
    }
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def write_execution_csv(items: List[ExecutionItem], path: PathLike) -> pathlib.Path:
    """Write the selection as a CSV list (import into a spreadsheet or tool)."""
    target = pathlib.Path(path)
    with target.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(["TestCaseID", "Name", "GroupPath", "Reason"])
        for it in items:
            writer.writerow([it.test_case_id, it.name, it.group_path, it.reason])
    return target


# Default XML template names — override these to match the real EXAM schema.
DEFAULT_XML_TEMPLATE = {
    "root_tag": "executionList",
    "item_tag": "testCase",
    "id_attr": "testCaseId",
    "name_attr": "name",
    "group_attr": "groupPath",
}


def write_execution_xml(
    items: List[ExecutionItem],
    path: PathLike,
    template: Optional[Dict[str, str]] = None,
) -> pathlib.Path:
    """Write a re-execution XML using an overridable element/attribute template.

    Once you know EXAM's exact schema, pass a *template* dict such as::

        {"root_tag": "TestExecution", "item_tag": "Test",
         "id_attr": "id", "name_attr": "title", "group_attr": "path"}

    and the selection logic stays untouched.
    """
    tpl = {**DEFAULT_XML_TEMPLATE, **(template or {})}
    root = Element(tpl["root_tag"], attrib={"count": str(len(items))})
    for it in items:
        SubElement(
            root,
            tpl["item_tag"],
            attrib={
                tpl["id_attr"]: it.test_case_id,
                tpl["name_attr"]: it.name,
                tpl["group_attr"]: it.group_path,
            },
        )
    pretty = minidom.parseString(tostring(root, encoding="utf-8")).toprettyxml(indent="  ")
    target = pathlib.Path(path)
    target.write_text(pretty, encoding="utf-8")
    return target


def build_reexecution(
    reports: Iterable[ExamReport],
    out_dir: PathLike,
    basename: str = "reexecution",
    formats: Iterable[str] = ("json", "csv", "xml"),
    predicate: Optional[Callable[[TestCase], bool]] = None,
    xml_template: Optional[Dict[str, str]] = None,
) -> Dict[str, pathlib.Path]:
    """One-call helper: select failures and write every requested format.

    Returns a ``{format: written_path}`` mapping.
    """
    reports = list(reports)
    items = select_failed(reports, predicate=predicate)
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    written: Dict[str, pathlib.Path] = {}
    if "json" in formats:
        written["json"] = write_execution_json(items, out / f"{basename}.json")
    if "csv" in formats:
        written["csv"] = write_execution_csv(items, out / f"{basename}.csv")
    if "xml" in formats:
        written["xml"] = write_execution_xml(items, out / f"{basename}.xml", xml_template)
    return written
