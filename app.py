import db
from exam_toolkit import parse_report
from flask import Flask, render_template, request, redirect, url_for
from pathlib import Path
from collections import defaultdict
from exam_toolkit import parse_report
from exam_toolkit.analyzer import cluster_by_signature
from datetime import datetime
from classifier import classify_defect
app = Flask(__name__)
db.init_db()
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Stockage simple en mémoire (pour ce projet, pas besoin de base de données ici)
STATE = {"reports": {}, "test_cases": []}
def compute_group_stats():
    """Regroupe pass/fail par groupe (ex: Root/Body/Windows)."""
    stats = defaultdict(lambda: {"PASS": 0, "FAIL": 0})
    for tc in STATE["test_cases"]:
        stats[tc.group_path_str][tc.final_valuation] += 1
    return dict(stats)


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        files = request.files.getlist("xml_files")
        reports = {}
        for f in files:
            if f.filename:
                save_path = UPLOAD_DIR / f.filename
                f.save(save_path)
                reports[f.filename] = parse_report(str(save_path))

        STATE["reports"] = reports
        STATE["test_cases"] = []
        for report in reports.values():
            STATE["test_cases"].extend(report.test_cases)

        db.save_import(list(reports.keys()), STATE["test_cases"])

        return redirect(url_for("dashboard"))

    return render_template("base.html", page="home")


@app.route("/dashboard")
def dashboard():
    test_cases = STATE["test_cases"]
    total = len(test_cases)
    passed = sum(1 for tc in test_cases if tc.final_valuation == "PASS")
    failed = sum(1 for tc in test_cases if tc.final_valuation == "FAIL")
    pass_rate = round((passed / total * 100), 1) if total else 0

    trend_data = db.get_trend_data()
    group_trend = db.get_group_trend_data()
    group_stats = compute_group_stats()

    current_time = datetime.now().strftime("%b %d, %Y, %I:%M %p")
    anomalies = db.detect_anomalies()
    return render_template(
        "dashboard.html",
        page="dashboard",
        total=total, passed=passed, failed=failed, pass_rate=pass_rate,
        group_stats=group_stats,
        trend_data=trend_data,
        group_trend=group_trend,
        current_time=current_time,
        anomalies=anomalies,
    )
    


@app.route("/tests")
def tests():
    test_cases = STATE["test_cases"]
    total = len(test_cases)
    passed = sum(1 for tc in test_cases if tc.final_valuation == "PASS")
    failed = sum(1 for tc in test_cases if tc.final_valuation == "FAIL")
    return render_template("tests.html", page="tests", test_cases=STATE["test_cases"])


@app.route("/analysis")
def analysis():
    clusters = []
    max_size = 1
    if STATE["reports"]:
        clusters = cluster_by_signature(list(STATE["reports"].values()))
        if clusters:
            max_size = max(c.size for c in clusters)
    return render_template("analysis.html", page="analysis", clusters=clusters, max_size=max_size)

@app.route("/test/<test_case_id>", methods=["GET", "POST"])
def test_detail(test_case_id):
    tc = next((t for t in STATE["test_cases"] if t.test_case_id == test_case_id), None)
    if tc is None:
        return "Test non trouvé", 404

    if request.method == "POST":
        comment = request.form.get("comment", "")
        defect_class = request.form.get("defect_class", "")
        rerun = request.form.get("rerun", "no")
        db.save_comment(test_case_id, "", comment, defect_class, rerun)
        return redirect(url_for("test_detail", test_case_id=test_case_id))

    history = db.get_comment_history(test_case_id)
    suggested_class, reason, confidence = ("Unclassified", "", "low")
    if tc.final_valuation == "FAIL":
     suggested_class, reason, confidence = classify_defect(tc.fails_text())
    return render_template(
        "test_detail.html",
        page="tests",
        tc=tc,
        history=history,
        suggested_class=suggested_class,
        suggestion_reason=reason,
        suggestion_confidence=confidence,
    )
@app.route("/history")
def history():
    imports = db.get_module_overview()
    return render_template("history.html", page="history", imports=imports)
@app.route("/ask", methods=["POST"])
def ask():
    question = request.json.get("question", "")
    answer = db.answer_question(question)
    return {"answer": answer}
@app.route("/compare")
def compare():
    imports = db.get_import_list()
    return render_template("compare.html", page="compare", imports=imports, result=None)


@app.route("/compare/run", methods=["POST"])
def compare_run():
    imports = db.get_import_list()
    id_a = int(request.form.get("import_a"))
    id_b = int(request.form.get("import_b"))
    result = db.compare_imports(id_a, id_b)
    return render_template("compare.html", page="compare", imports=imports, result=result, selected_a=id_a, selected_b=id_b)

if __name__ == "__main__":
    app.run(debug=True)