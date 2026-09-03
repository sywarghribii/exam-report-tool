# EXAM Report Toolkit

A small, reusable toolkit for **extracting, analysing and reporting** on EXAM
test reports (the `examReport` XML format). It grew out of a single "XML →
Excel" script and is now organised so the extraction layer can be imported as
a **helper library in any other code**, with the Excel export, analysis and
GUI sitting on top as optional layers.

> No confidential data is included. A **synthetic sample generator**
> (`examples/generate_sample_xml.py`) produces realistic, made-up reports so
> the whole toolkit is runnable and demoable without any real report files.

---

## What it does

- **Extraction** — parse the nested `<groups>/<group>` hierarchy, attach the
  full group path to every `<testCase>`, and read metadata and subtests.
- **Fails column** — for each test case, collect *all* failing `<subtests>`
  (a test case can have several) into one readable field, plus a `FailCount`.
- **Reporting comments** — attach human-written comments + a rerun flag to
  test cases, persisted in a sidecar JSON keyed by `TestCaseID` (survives
  re-runs; never duplicates confidential XML content).
- **Smart analyzer** — cluster failures by *signature* (identical patterns,
  numbers/timestamps normalised away) and by *fuzzy similarity*
  (near-duplicates), plus roll-up stats and top failing groups.
- **Re-execution files** — select the failed test cases and export re-run
  manifests in JSON / CSV / XML (the XML schema is template-driven so you can
  match your real EXAM import format).
- **Excel export** — one formatted sheet per report (with the Fails and
  reporting columns), plus optional `Summary` and `Fail Analysis` sheets.
- **GUI + CLI** — a tkinter front-end and a terminal/CI-friendly CLI.

---

## Project layout

```
exam_toolkit/            the importable library
  models.py              typed data: TestCase, Subtest, ExamReport, …
  extractor.py           parse XML → models, models → flat rows   ← import this
  comments.py            persistent reporting comments (sidecar JSON)
  analyzer.py            fail clustering + statistics
  reexecution.py         build re-run execution files
  excel_export.py        formatted .xlsx output
  gui.py                 optional tkinter front-end
  cli.py                 command-line interface
examples/                runnable examples + synthetic data generator
tests/                   standalone/pytest test suite
sample_data/             generated on demand (gitignore in real use)
```

**Dependency boundary:** `models`, `extractor`, `comments`, `analyzer`,
`reexecution` use only the **standard library**. Only `excel_export` (and the
Excel path of the CLI/GUI) needs `pandas` + `openpyxl`.

---

## Quick start

```bash
pip install -r requirements.txt

# 1) make some synthetic reports to play with
python examples/generate_sample_xml.py

# 2) run the examples
python examples/example_01_basic_extraction.py
python examples/example_02_fail_analysis.py
python examples/example_03_report_and_export.py
python examples/example_04_reexecution.py

# 3) or use the CLI
python -m exam_toolkit.cli summary sample_data/*.xml
python -m exam_toolkit.cli export  sample_data/*.xml -o out.xlsx
python -m exam_toolkit.cli reexec  sample_data/*.xml -d ./reexec

# 4) or the GUI
python -m exam_toolkit.gui
```

## Using it as a library (feature #1)

```python
from exam_toolkit import parse_report, cluster_by_signature

report = parse_report("run.xml")
print(report.summary())                 # {'total':.., 'passed':.., 'failed':..}

for tc in report.failed():              # only failed test cases
    print(tc.test_case_id, tc.group_path_str)
    print(tc.fails_text())              # all failing subtests, one per line

for cluster in cluster_by_signature([report])[:5]:
    print(cluster.size, cluster.signature)
```

Every parse function has a string variant (`parse_report_string`) for
in-memory data (web uploads, tests) so you never have to touch disk.

---

## The "Fails" column (feature #2)

A `<testCase>` may contain several failing `<subtests>`. `TestCase.fails_text()`
joins them into one cell, each line being the subtest name plus its
`subtestItems`, e.g.:

```
FH Position Geschlossen von FahrerTuer nicht angesteuert, weil FH nicht normiert (Fenster=FahrerTuer, Soll Position=Geschlossen, Normiert=0)
```

`FailCount` gives the number of failing subtests. Final valuation is treated
as authoritative; pass `use_initial=True` to inspect first-run verdicts.

## Reporting comments (feature #3)

Comments live in a JSON store keyed by `TestCaseID` and are merged into the
`Reporting Comment` / `Rerun` columns at export time. Seed a blank store with
every failure so a reviewer has a ready-to-fill checklist:

```python
from exam_toolkit import CommentStore, seed_store_from_failures
store = CommentStore("comments.json")
seed_store_from_failures([tc.test_case_id for tc in report.failed()], store)
store.set("TC_00123", comment="Known flaky sensor, JIRA-42", rerun="yes")
store.save()
```

---

## Internship roadmap (feature #4)

This repo is structured to *be* the foundation of the tool. Suggested phases:

1. **Confirm the real schema** against a redacted sample: verify the tags
   (`testCase`, `subtests`, `metadataItem`) and the re-execution import format
   EXAM expects, then override `reexecution.DEFAULT_XML_TEMPLATE`.
2. **Reporting** — done: Excel export with Fails + comments + summary.
3. **Smart analyzer** — extend `analyzer.py`: weight clusters by group, trend
   fail signatures across runs, flag likely-flaky tests (pass↔fail flips).
4. **Clustering of fails** — signature + similarity are provided; a natural
   next step is embedding-based clustering behind the same `FailCluster` API.
5. **Re-execution** — swap in the confirmed EXAM format; add a filter for
   "won't-fix"/known-defect tests using the comment store's `category`.
6. **Front-end** — the tkinter GUI is a starting point; the clean library API
   makes a later web dashboard straightforward.

Because every layer talks through the typed models, you can replace or extend
any single piece without touching the others.

---

## Testing

```bash
python tests/test_toolkit.py     # standalone
# or:  pytest tests/
```
# EXAM Report Tool

A web application built with Flask to import, analyze, and visualize EXAM test reports.

## Features
- Import one or multiple EXAM XML reports
- Test case table with filters and failure details
- Automatic failure clustering (grouping similar failures)
- Interactive dashboard with charts (trend over time, per-module results, pass rate)
- Persistent review/comment system per test case (SQLite)
- Excel export
- Compare two runs (fixed / regressed / unchanged tests)
- Simple rule-based defect classification
- Built-in chatbot to ask questions about the results

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/sywarghribii/exam-report-tool.git
cd exam-report-tool
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

```

### 3. Run the application
```bash
python app.py
```

### 4. Open in your browser
http://127.0.0.1:5000

## Tech Stack
- **Backend**: Python, Flask
- **Database**: SQLite
- **Frontend**: HTML, Jinja2, Bootstrap, Chart.js
- **Core logic**: exam_toolkit (provided report parsing/analysis library)

## Project Structure