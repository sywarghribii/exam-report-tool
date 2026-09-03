"""
comments.py
===========

Reporting layer: attach human-written comments and a rerun flag to test
cases and persist them independently of the (read-only, confidential) XML
reports.

Why a separate store?
---------------------
The reporting text is created by an engineer *during triage* — it does not
live in the EXAM XML.  Keeping it in a small sidecar JSON file, keyed by
``TestCaseID``, means:

* the comments survive re-runs and re-exports,
* the same comment automatically re-attaches when a test appears in a later
  report, and
* nothing confidential from the XML is duplicated into the store.

Example
-------
>>> store = CommentStore.load("comments.json")
>>> store.set("TC_00123", comment="Known flaky sensor, ticket JIRA-42", rerun="yes")
>>> store.save()
>>> rows = merge_comments(rows, store)   # fills the reporting columns
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import asdict, dataclass, field
from typing import Dict, Iterable, List, Optional, Union

PathLike = Union[str, pathlib.Path]


@dataclass
class Comment:
    """One reporting entry for a single test case."""

    comment: str = ""
    rerun: str = ""          # free text or a flag such as "yes"/"no"
    category: str = ""       # optional triage bucket, e.g. "Environment"
    author: str = ""
    updated_at: str = ""     # ISO timestamp, filled on save


class CommentStore:
    """A dictionary-like store of :class:`Comment` keyed by ``TestCaseID``.

    Backed by a JSON file so it is human-readable, diff-able and trivially
    shareable between teammates.
    """

    def __init__(self, path: Optional[PathLike] = None,
                 data: Optional[Dict[str, Comment]] = None):
        self.path: Optional[pathlib.Path] = pathlib.Path(path) if path else None
        self._data: Dict[str, Comment] = data or {}

    # ---- construction ----------------------------------------------------
    @classmethod
    def load(cls, path: PathLike) -> "CommentStore":
        """Load a store from *path*; returns an empty store if it doesn't exist."""
        p = pathlib.Path(path)
        if not p.exists():
            return cls(path=p)
        raw = json.loads(p.read_text(encoding="utf-8"))
        data = {tc_id: Comment(**fields) for tc_id, fields in raw.items()}
        return cls(path=p, data=data)

    # ---- access ----------------------------------------------------------
    def get(self, test_case_id: str) -> Optional[Comment]:
        return self._data.get(test_case_id)

    def set(self, test_case_id: str, **fields) -> Comment:
        """Create or update the comment for *test_case_id*."""
        existing = self._data.get(test_case_id, Comment())
        for key, value in fields.items():
            if not hasattr(existing, key):
                raise AttributeError(f"Comment has no field {key!r}")
            setattr(existing, key, value)
        self._data[test_case_id] = existing
        return existing

    def __contains__(self, test_case_id: str) -> bool:
        return test_case_id in self._data

    def __len__(self) -> int:
        return len(self._data)

    # ---- persistence -----------------------------------------------------
    def save(self, path: Optional[PathLike] = None) -> pathlib.Path:
        """Write the store to disk as JSON (stamps ``updated_at``)."""
        from datetime import datetime, timezone

        target = pathlib.Path(path) if path else self.path
        if target is None:
            raise ValueError("No path given and store has no default path.")
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for c in self._data.values():
            if not c.updated_at:
                c.updated_at = stamp
        payload = {tc_id: asdict(c) for tc_id, c in self._data.items()}
        target.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        self.path = target
        return target


def merge_comments(rows: List[Dict[str, str]], store: CommentStore) -> List[Dict[str, str]]:
    """Fill the ``Reporting Comment`` / ``Rerun`` columns of *rows* from *store*.

    Matches on the ``TestCaseID`` field.  Returns the same list (mutated in
    place) for convenient chaining.
    """
    for row in rows:
        comment = store.get(row.get("TestCaseID", ""))
        if comment is not None:
            row["Reporting Comment"] = comment.comment
            row["Rerun"] = comment.rerun
            if comment.category:
                row["Comment Category"] = comment.category
    return rows


def seed_store_from_failures(
    test_case_ids: Iterable[str], store: CommentStore, default_category: str = ""
) -> CommentStore:
    """Pre-create blank comment rows for a set of failing test cases.

    Handy to hand a reviewer a ready-to-fill JSON with every failure listed.
    """
    for tc_id in test_case_ids:
        if tc_id not in store:
            store.set(tc_id, category=default_category)
    return store
