"""
models.py
=========

Typed, framework-agnostic data structures for EXAM report data.

These dataclasses are the shared "language" of the whole toolkit.  Every
other module (extraction, analysis, Excel export, re-execution) consumes or
produces these objects instead of loose dicts, so downstream code stays
readable and refactor-safe.

Nothing here depends on tkinter, pandas or openpyxl — you can import this
module in any script, notebook or web backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# EXAM verdicts we treat as a failure.  Kept in one place so the whole
# toolkit agrees on what "failed" means.
FAIL_VERDICTS = {"FAIL", "ERROR"}
PASS_VERDICTS = {"PASS", "SUCCESS", "OK"}


def is_fail_verdict(verdict: Optional[str]) -> bool:
    """Return True if *verdict* counts as a failure (case-insensitive)."""
    return (verdict or "").strip().upper() in FAIL_VERDICTS


@dataclass
class SubtestItem:
    """A single key/value row inside a subtest (``<subtestItems>``)."""

    key: str
    value: str


@dataclass
class Subtest:
    """A ``<subtests>`` element: one assertion / check inside a test case."""

    name: str
    initial_valuation: str = ""
    final_valuation: str = ""
    timestamp: str = ""
    type: str = ""
    items: List[SubtestItem] = field(default_factory=list)

    @property
    def is_fail(self) -> bool:
        """True when the *final* verdict is a failure.

        Final valuation is authoritative because it reflects the verdict
        after any manual re-valuation.  Use :meth:`is_fail_initial` if you
        need the raw first-run verdict instead.
        """
        return is_fail_verdict(self.final_valuation)

    @property
    def is_fail_initial(self) -> bool:
        """True when the *first-run* verdict is a failure."""
        return is_fail_verdict(self.initial_valuation)

    def items_as_dict(self) -> Dict[str, str]:
        """Return the subtest items as an ordered ``{key: value}`` mapping."""
        return {it.key: it.value for it in self.items}

    def describe(self, include_items: bool = True) -> str:
        """Human-readable one-line description, e.g. for an Excel cell.

        ``FH Position ... (Fenster=FahrerTuer, Soll Position=Geschlossen)``
        """
        if include_items and self.items:
            joined = ", ".join(f"{it.key}={it.value}" for it in self.items)
            return f"{self.name} ({joined})"
        return self.name


@dataclass
class TestCase:
    """A ``<testCase>`` element plus its group path, metadata and subtests."""

    test_case_id: str = ""
    name: str = ""
    start_time: str = ""
    duration: str = ""
    initial_valuation: str = ""
    final_valuation: str = ""
    type: str = ""
    group_path: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    subtests: List[Subtest] = field(default_factory=list)

    # ---- verdict helpers -------------------------------------------------
    @property
    def is_fail(self) -> bool:
        """True when the test case's final verdict is a failure."""
        return is_fail_verdict(self.final_valuation)

    @property
    def group_path_str(self) -> str:
        """The group hierarchy joined for display: ``A / B / C``."""
        return " / ".join(self.group_path)

    # ---- subtest helpers -------------------------------------------------
    def failed_subtests(self, use_initial: bool = False) -> List[Subtest]:
        """Return every subtest that failed.

        By default this looks at the *final* verdict; pass
        ``use_initial=True`` to inspect first-run verdicts instead.
        """
        if use_initial:
            return [s for s in self.subtests if s.is_fail_initial]
        return [s for s in self.subtests if s.is_fail]

    @property
    def fail_count(self) -> int:
        """Number of failed subtests (final verdict)."""
        return len(self.failed_subtests())

    def fails_text(self, separator: str = "\n", include_items: bool = True) -> str:
        """All failing subtests as a single string (great for one Excel cell).

        Each failing subtest becomes one line; *separator* joins them.
        """
        return separator.join(
            s.describe(include_items=include_items) for s in self.failed_subtests()
        )

    def meta(self, label: str, default: str = "") -> str:
        """Convenience getter for a metadata item by label."""
        return self.metadata.get(label, default)


@dataclass
class ExamReport:
    """A whole parsed report file: an ordered list of test cases."""

    source: str = ""  # file path or name the report came from
    test_cases: List[TestCase] = field(default_factory=list)

    def __iter__(self):
        return iter(self.test_cases)

    def __len__(self) -> int:
        return len(self.test_cases)

    # ---- filtering helpers ----------------------------------------------
    def failed(self) -> List[TestCase]:
        """Only the test cases whose final verdict is a failure."""
        return [tc for tc in self.test_cases if tc.is_fail]

    def passed(self) -> List[TestCase]:
        """Only the test cases whose final verdict is not a failure."""
        return [tc for tc in self.test_cases if not tc.is_fail]

    # ---- quick stats -----------------------------------------------------
    def summary(self) -> Dict[str, int]:
        """Counts that are handy for a report header / dashboard."""
        total = len(self.test_cases)
        failed = len(self.failed())
        return {
            "total": total,
            "passed": total - failed,
            "failed": failed,
            "failed_subtests": sum(tc.fail_count for tc in self.test_cases),
        }
