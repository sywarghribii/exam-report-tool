"""
analyzer.py
===========

The "smart analyzer": turn a pile of failures into insight.

It offers two complementary views:

1. **Signature clustering** — normalise each failing subtest into a
   *signature* (strip volatile bits like numbers, GUIDs, timestamps) and
   group identical signatures.  Fast, deterministic, explainable.

2. **Similarity clustering** — group failures whose messages are *similar*
   (not necessarily identical) using :mod:`difflib`.  Catches near-duplicates
   that signature-normalisation misses, with no external ML dependency.

Both return the same :class:`FailCluster` shape so the reporting/export code
doesn't care which strategy produced them.

Everything works on the typed models from :mod:`exam_toolkit.models`.
"""

from __future__ import annotations

import difflib
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple

from .models import ExamReport, Subtest, TestCase

# ----------------------------------------------------------------------
# Signature normalisation
# ----------------------------------------------------------------------
# Order matters: apply the most specific patterns first.
_NORMALISERS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b\d{4}-\d{2}-\d{2}[T ][\d:.+\-]+"), "<TIME>"),          # timestamps
    (re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}\b"), "<UUID>"),       # UUIDs
    (re.compile(r"0x[0-9a-fA-F]+"), "<HEX>"),                              # hex values
    (re.compile(r"[-+]?\d+[.,]\d+"), "<NUM>"),                             # decimals
    (re.compile(r"[-+]?\d+"), "<NUM>"),                                    # integers
    (re.compile(r"\s+"), " "),                                             # whitespace
]


def normalise_signature(text: str) -> str:
    """Reduce a failure message to a stable *signature*.

    Numbers, timestamps, UUIDs and hex are replaced by placeholders so that
    "Position 512 != 0" and "Position 47 != 0" collapse to one signature.
    """
    sig = text.strip()
    for pattern, repl in _NORMALISERS:
        sig = pattern.sub(repl, sig)
    return sig.strip()


def subtest_signature(subtest: Subtest, include_items: bool = True) -> str:
    """Signature for a failing subtest: normalised name (+ item keys)."""
    base = normalise_signature(subtest.name)
    if include_items and subtest.items:
        # Item *keys* are structural; values are volatile, so key-only keeps
        # the signature stable across differing measured values.
        keys = ",".join(sorted(it.key for it in subtest.items))
        return f"{base} | keys[{keys}]"
    return base


# ----------------------------------------------------------------------
# Result shapes
# ----------------------------------------------------------------------
@dataclass
class FailOccurrence:
    """One failing subtest, tagged with which test case it came from."""

    test_case_id: str
    test_case_name: str
    group_path: str
    subtest_name: str
    subtest: Subtest


@dataclass
class FailCluster:
    """A group of failures that share a signature / are mutually similar."""

    signature: str
    occurrences: List[FailOccurrence] = field(default_factory=list)

    @property
    def size(self) -> int:
        """Number of failing subtests in the cluster."""
        return len(self.occurrences)

    @property
    def affected_test_cases(self) -> List[str]:
        """Distinct test-case IDs touched by this cluster (sorted)."""
        return sorted({o.test_case_id for o in self.occurrences})

    def example(self) -> str:
        """A representative raw subtest description for display."""
        return self.occurrences[0].subtest.describe() if self.occurrences else ""


# ----------------------------------------------------------------------
# Collecting failures
# ----------------------------------------------------------------------
def collect_fail_occurrences(
    reports: Iterable[ExamReport], use_initial: bool = False
) -> List[FailOccurrence]:
    """Flatten one or more reports into a list of failing-subtest occurrences."""
    occurrences: List[FailOccurrence] = []
    for report in reports:
        for tc in report.test_cases:
            for st in tc.failed_subtests(use_initial=use_initial):
                occurrences.append(
                    FailOccurrence(
                        test_case_id=tc.test_case_id,
                        test_case_name=tc.name,
                        group_path=tc.group_path_str,
                        subtest_name=st.name,
                        subtest=st,
                    )
                )
    return occurrences


# ----------------------------------------------------------------------
# Strategy 1: signature clustering
# ----------------------------------------------------------------------
def cluster_by_signature(
    reports: Iterable[ExamReport],
    include_items: bool = True,
    use_initial: bool = False,
) -> List[FailCluster]:
    """Group failing subtests by normalised signature, largest cluster first."""
    occurrences = collect_fail_occurrences(reports, use_initial=use_initial)
    buckets: Dict[str, FailCluster] = {}
    for occ in occurrences:
        sig = subtest_signature(occ.subtest, include_items=include_items)
        buckets.setdefault(sig, FailCluster(signature=sig)).occurrences.append(occ)
    return sorted(buckets.values(), key=lambda c: c.size, reverse=True)


# ----------------------------------------------------------------------
# Strategy 2: fuzzy similarity clustering
# ----------------------------------------------------------------------
def cluster_by_similarity(
    reports: Iterable[ExamReport],
    threshold: float = 0.82,
    use_initial: bool = False,
) -> List[FailCluster]:
    """Greedy near-duplicate clustering using string similarity.

    *threshold* is the minimum :class:`difflib.SequenceMatcher` ratio (0..1)
    for two failure messages to land in the same cluster.  Higher = stricter.
    """
    occurrences = collect_fail_occurrences(reports, use_initial=use_initial)
    clusters: List[FailCluster] = []

    for occ in occurrences:
        text = normalise_signature(occ.subtest.name)
        placed = False
        for cluster in clusters:
            ratio = difflib.SequenceMatcher(None, text, cluster.signature).ratio()
            if ratio >= threshold:
                cluster.occurrences.append(occ)
                placed = True
                break
        if not placed:
            clusters.append(FailCluster(signature=text, occurrences=[occ]))

    return sorted(clusters, key=lambda c: c.size, reverse=True)


# ----------------------------------------------------------------------
# Roll-up statistics
# ----------------------------------------------------------------------
def top_failing_groups(reports: Iterable[ExamReport], limit: int = 10) -> List[Tuple[str, int]]:
    """Most failure-heavy group paths, as ``(group_path, fail_count)`` pairs."""
    counter: Counter = Counter()
    for report in reports:
        for tc in report.test_cases:
            if tc.is_fail:
                counter[tc.group_path_str or "(root)"] += 1
    return counter.most_common(limit)


def failure_overview(reports: Iterable[ExamReport]) -> Dict[str, int]:
    """A compact dashboard-style summary across all supplied reports."""
    reports = list(reports)
    total = passed = failed = fail_subtests = 0
    for report in reports:
        s = report.summary()
        total += s["total"]
        passed += s["passed"]
        failed += s["failed"]
        fail_subtests += s["failed_subtests"]
    clusters = cluster_by_signature(reports)
    return {
        "reports": len(reports),
        "test_cases": total,
        "passed": passed,
        "failed": failed,
        "failed_subtests": fail_subtests,
        "distinct_fail_signatures": len(clusters),
    }


def clusters_to_rows(clusters: List[FailCluster]) -> List[Dict[str, str]]:
    """Flatten clusters into tabular rows for an Excel "Fail Analysis" sheet."""
    rows: List[Dict[str, str]] = []
    for rank, cluster in enumerate(clusters, start=1):
        rows.append(
            {
                "Rank": rank,
                "Occurrences": cluster.size,
                "AffectedTestCases": len(cluster.affected_test_cases),
                "Signature": cluster.signature,
                "Example": cluster.example(),
                "TestCaseIDs": ", ".join(cluster.affected_test_cases),
            }
        )
    return rows
