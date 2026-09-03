"""
test_toolkit.py
===============

Runs with pytest *or* standalone (`python tests/test_toolkit.py`).
Uses a tiny inline XML fixture — no external / confidential files needed.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from exam_toolkit import (
    CommentStore,
    cluster_by_signature,
    merge_comments,
    normalise_signature,
    parse_report_string,
    report_to_rows,
    select_failed,
)

SAMPLE_XML = """<?xml version="1.0"?>
<examReport>
  <groups name="Root">
    <group name="Body">
      <group name="Windows">
        <testCase testCaseId="TC_1" name="Win Test 1" initialValuation="FAIL" finalValuation="FAIL" type="TestCase">
          <metadata>
            <metadata><metadataItem label="Platform" value="MLB"/></metadata>
          </metadata>
          <subtests name="Position 512 not reached" initialValuation="FAIL" finalValuation="FAIL" type="TableSubtest">
            <subtestItems key="Fenster" value="FahrerTuer"/>
            <subtestItems key="Normiert" value="0"/>
          </subtests>
          <subtests name="Sensor ok" initialValuation="PASS" finalValuation="PASS" type="TableSubtest"/>
        </testCase>
        <testCase testCaseId="TC_2" name="Win Test 2" initialValuation="PASS" finalValuation="PASS" type="TestCase">
          <subtests name="Position 3 not reached" initialValuation="PASS" finalValuation="PASS" type="TableSubtest"/>
        </testCase>
      </group>
    </group>
    <group name="Comfort">
      <testCase testCaseId="TC_3" name="Comfort 1" initialValuation="FAIL" finalValuation="FAIL" type="TestCase">
        <subtests name="Position 47 not reached" initialValuation="FAIL" finalValuation="FAIL" type="TableSubtest">
          <subtestItems key="Fenster" value="BeifahrerTuer"/>
          <subtestItems key="Normiert" value="0"/>
        </subtests>
      </testCase>
    </group>
  </groups>
</examReport>
"""


def _report():
    return parse_report_string(SAMPLE_XML, source="fixture.xml")


def test_parse_counts_and_paths():
    r = _report()
    assert len(r) == 3
    s = r.summary()
    assert s == {"total": 3, "passed": 1, "failed": 2, "failed_subtests": 2}
    tc1 = next(tc for tc in r if tc.test_case_id == "TC_1")
    assert tc1.group_path == ["Root", "Body", "Windows"]
    assert tc1.group_path_str == "Root / Body / Windows"


def test_failed_subtests_and_fails_text():
    r = _report()
    tc1 = next(tc for tc in r if tc.test_case_id == "TC_1")
    assert tc1.fail_count == 1
    fails = tc1.fails_text()
    assert "Position 512 not reached" in fails
    assert "Fenster=FahrerTuer" in fails
    # passing subtest must NOT appear
    assert "Sensor ok" not in fails


def test_row_flattening_has_fails_column():
    r = _report()
    rows = report_to_rows(r)
    row1 = next(x for x in rows if x["TestCaseID"] == "TC_1")
    assert "Fails" in row1 and row1["FailCount"] == 1
    assert row1["Reporting Comment"] == "" and row1["Rerun"] == ""


def test_signature_clustering_merges_numeric_variants():
    r = _report()
    # "Position 512..." and "Position 47..." should collapse to one signature
    clusters = cluster_by_signature([r])
    top = clusters[0]
    assert top.size == 2
    assert "<NUM>" in top.signature


def test_normalise_signature():
    a = normalise_signature("Position 512 != 0")
    b = normalise_signature("Position 47 != 999")
    assert a == b == "Position <NUM> != <NUM>"


def test_comments_merge():
    r = _report()
    rows = report_to_rows(r)
    store = CommentStore()
    store.set("TC_1", comment="flaky", rerun="yes")
    merge_comments(rows, store)
    row1 = next(x for x in rows if x["TestCaseID"] == "TC_1")
    assert row1["Reporting Comment"] == "flaky" and row1["Rerun"] == "yes"


def test_select_failed_dedup():
    r = _report()
    items = select_failed([r, r])  # same report twice
    ids = [i.test_case_id for i in items]
    assert sorted(ids) == ["TC_1", "TC_3"]  # deduped, only failures


def _run_standalone():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS  {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests passed")


if __name__ == "__main__":
    _run_standalone()
