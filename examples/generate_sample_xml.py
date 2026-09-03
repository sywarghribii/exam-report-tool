"""
generate_sample_xml.py
=======================

Create **synthetic** EXAM report XML files that mimic the real ``examReport``
structure — nested groups, test cases, metadata and failing subtests — with
entirely made-up, non-confidential data.

Use these to develop, test and demo the toolkit without ever touching the
real (confidential) reports.

Run:
    python examples/generate_sample_xml.py            # -> sample_data/*.xml
    python examples/generate_sample_xml.py --cases 60 # more test cases
"""

from __future__ import annotations

import argparse
import pathlib
import random
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

# Fake, non-confidential building blocks.
GROUPS = {
    "Body": ["Windows", "Doors", "Seats"],
    "Comfort": ["Climate", "Lighting"],
    "Powertrain": ["Engine", "Transmission"],
}
WINDOWS = ["FahrerTuer", "BeifahrerTuer", "HintenLinks", "HintenRechts"]
POSITIONS = ["Geschlossen", "Offen", "Komfortoeffnung"]
PLATFORMS = ["MLB", "MEB", "PPE"]
PROJECTS = ["PROJ_A", "PROJ_B", "PROJ_C"]
VARIANTS = ["V1", "V2", "V3"]


def _make_subtest(parent: Element, fail: bool, rng: random.Random) -> None:
    verdict = "FAIL" if fail else "PASS"
    window = rng.choice(WINDOWS)
    position = rng.choice(POSITIONS)
    st = SubElement(
        parent,
        "subtests",
        {
            "name": f"FH Position {position} von {window} "
                    f"{'nicht angesteuert, weil FH nicht normiert' if fail else 'korrekt angesteuert'}",
            "initialValuation": verdict,
            "finalValuation": verdict,
            "timestamp": "2026-07-15T16:14:20.196+02:00[Europe/Berlin]",
            "type": "TableSubtest",
        },
    )
    for key, value in (
        ("Fenster", window),
        ("Soll Position", position),
        ("Soll Oeffnung", str(rng.randint(-1, 100))),
        ("Normiert", str(rng.randint(0, 1))),
    ):
        SubElement(st, "subtestItems", {"key": key, "value": value})


def _make_test_case(parent: Element, idx: int, rng: random.Random) -> None:
    fail = rng.random() < 0.35
    tc = SubElement(
        parent,
        "testCase",
        {
            "testCaseId": f"TC_{idx:05d}",
            "name": f"Fensterheber Funktionstest {idx}",
            "starttime": "2026-07-15T16:10:00.000+02:00",
            "duration": str(rng.randint(5, 300)),
            "initialValuation": "FAIL" if fail else "PASS",
            "finalValuation": "FAIL" if fail else "PASS",
            "type": "TestCase",
        },
    )
    md = SubElement(tc, "metadata")
    for label, value in (
        ("Variante", rng.choice(VARIANTS)),
        ("Platform", rng.choice(PLATFORMS)),
        ("Projekt", rng.choice(PROJECTS)),
        ("Link", f"http://exam.internal/tc/{idx}"),
    ):
        SubElement(md, "metadataItem", {"label": label, "value": value})

    # subtests: failing cases get 1-3 fail subtests plus some passing ones
    n_pass = rng.randint(1, 3)
    for _ in range(n_pass):
        _make_subtest(tc, fail=False, rng=rng)
    if fail:
        for _ in range(rng.randint(1, 3)):
            _make_subtest(tc, fail=True, rng=rng)


def build_report(n_cases: int, seed: int) -> Element:
    rng = random.Random(seed)
    root = Element("examReport", {"generated": "synthetic"})
    groups = SubElement(root, "groups", {"name": "Root"})

    idx = 1
    for top_name, subnames in GROUPS.items():
        top = SubElement(groups, "group", {"name": top_name})
        for sub_name in subnames:
            sub = SubElement(top, "group", {"name": sub_name})
            for _ in range(max(1, n_cases // (len(GROUPS) * 3))):
                _make_test_case(sub, idx, rng)
                idx += 1
    return root


def write_report(root: Element, path: pathlib.Path) -> None:
    pretty = minidom.parseString(tostring(root, encoding="utf-8")).toprettyxml(indent="  ")
    path.write_text(pretty, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate synthetic EXAM reports.")
    ap.add_argument("--cases", type=int, default=45, help="approx. test cases per file")
    ap.add_argument("--files", type=int, default=2, help="how many report files")
    ap.add_argument(
        "--out",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parent.parent / "sample_data",
        help="output directory",
    )
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    for i in range(args.files):
        root = build_report(args.cases, seed=1000 + i)
        path = args.out / f"sample_report_{i + 1}.xml"
        write_report(root, path)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
