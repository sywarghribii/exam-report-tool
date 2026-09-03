import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path("exam_reports.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS imports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imported_at TEXT NOT NULL,
            filenames TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_id INTEGER NOT NULL,
            test_case_id TEXT NOT NULL,
            name TEXT,
            group_path TEXT,
            status TEXT,
            fails_text TEXT,
            FOREIGN KEY (import_id) REFERENCES imports(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_case_id TEXT NOT NULL,
            comment TEXT,
            defect_class TEXT,
            rerun TEXT,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_import(filenames, test_cases):
    """Sauvegarde un nouvel import et ses tests. Retourne l'id de l'import."""
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO imports (imported_at, filenames) VALUES (?, ?)",
        (datetime.now().isoformat(), json.dumps(filenames)),
    )
    import_id = cur.lastrowid

    for tc in test_cases:
        fails = tc.fails_text() if tc.final_valuation == "FAIL" else ""
        conn.execute(
            """INSERT INTO test_cases
               (import_id, test_case_id, name, group_path, status, fails_text)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (import_id, tc.test_case_id, tc.name, tc.group_path_str, tc.final_valuation, fails),
        )
    conn.commit()
    conn.close()
    return import_id


def get_latest_test_cases():
    """Renvoie les tests du dernier import (le plus récent)."""
    conn = get_connection()
    latest = conn.execute("SELECT id FROM imports ORDER BY id DESC LIMIT 1").fetchone()
    if not latest:
        conn.close()
        return []
    rows = conn.execute(
        "SELECT * FROM test_cases WHERE import_id = ?", (latest["id"],)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_imports():
    """Renvoie l'historique de tous les imports."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM imports ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_test_cases_for_import(import_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM test_cases WHERE import_id = ?", (import_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_comment(test_case_id, comment, defect_class, rerun):
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM comments WHERE test_case_id = ?", (test_case_id,)
    ).fetchone()

    if existing:
        conn.execute(
            """UPDATE comments SET comment=?, defect_class=?, rerun=?, updated_at=?
               WHERE test_case_id=?""",
            (comment, defect_class, rerun, datetime.now().isoformat(), test_case_id),
        )
    else:
        conn.execute(
            """INSERT INTO comments (test_case_id, comment, defect_class, rerun, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (test_case_id, comment, defect_class, rerun, datetime.now().isoformat()),
        )
    conn.commit()
    conn.close()


def get_comment(test_case_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM comments WHERE test_case_id = ?", (test_case_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
def get_comment_history(test_case_id):
    """Renvoie toutes les revues passées pour ce test, les plus récentes d'abord."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM comments WHERE test_case_id = ? ORDER BY updated_at DESC",
        (test_case_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_comments():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM comments ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
def get_trend_data():
    conn = get_connection()
    rows = conn.execute("""
        SELECT i.imported_at, tc.status, COUNT(*) as count
        FROM test_cases tc
        JOIN imports i ON tc.import_id = i.id
        GROUP BY i.id, tc.status
        ORDER BY i.imported_at
    """).fetchall()
    conn.close()

    trend = {}
    for r in rows:
        date = r["imported_at"][:16]  # coupe pour lisibilité
        trend.setdefault(date, {"PASS": 0, "FAIL": 0})
        trend[date][r["status"]] = r["count"]

    return trend
def get_group_trend_data():
    """Renvoie l'évolution passed/failed par groupe ET par date d'import."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT i.imported_at, tc.group_path, tc.status, COUNT(*) as count
        FROM test_cases tc
        JOIN imports i ON tc.import_id = i.id
        GROUP BY i.id, tc.group_path, tc.status
        ORDER BY i.imported_at
    """).fetchall()
    conn.close()

    # Structure : { "Root/Body/Windows": { "2026-08-20 11:53": {"PASS": 5, "FAIL": 2}, ... }, ... }
    trend = {}
    for r in rows:
        group = r["group_path"]
        date = r["imported_at"][:16]
        trend.setdefault(group, {})
        trend[group].setdefault(date, {"PASS": 0, "FAIL": 0})
        trend[group][date][r["status"]] = r["count"]

    return trend
def get_imports_with_results():
    """Renvoie chaque import avec son résultat global (PASSED/FAILED) et son nombre de tests."""
    conn = get_connection()
    imports = conn.execute("SELECT * FROM imports ORDER BY id DESC").fetchall()
    result = []
    for imp in imports:
        counts = conn.execute(
            "SELECT status, COUNT(*) as c FROM test_cases WHERE import_id = ? GROUP BY status",
            (imp["id"],),
        ).fetchall()
        counts_dict = {r["status"]: r["c"] for r in counts}
        failed = counts_dict.get("FAIL", 0)
        overall = "FAILED" if failed > 0 else "PASSED"
        result.append({
            "id": imp["id"],
            "imported_at": imp["imported_at"],
            "filenames": imp["filenames"],
            "overall": overall,
            "total": sum(counts_dict.values()),
        })
    conn.close()
    return result
def get_test_plans_overview():
    """Regroupe les imports par nom de fichier ('plan de test'), garde la dernière exécution de chacun."""
    conn = get_connection()
    imports = conn.execute("SELECT * FROM imports ORDER BY id ASC").fetchall()

    plans = {}
    for imp in imports:
        filenames = json.loads(imp["filenames"])
        if not filenames:
            continue
        plan_name = ", ".join(filenames)

        counts = conn.execute(
            "SELECT status, COUNT(*) as c FROM test_cases WHERE import_id = ? GROUP BY status",
            (imp["id"],),
        ).fetchall()
        counts_dict = {r["status"]: r["c"] for r in counts}
        overall = "FAILED" if counts_dict.get("FAIL", 0) > 0 else "PASSED"

        previous_run_count = plans.get(plan_name, {}).get("run_count", 0)

        plans[plan_name] = {
            "plan_name": plan_name,
            "imported_at": imp["imported_at"],
            "overall": overall,
            "total": sum(counts_dict.values()),
            "run_count": previous_run_count + 1,
        }

    conn.close()
    return sorted(plans.values(), key=lambda p: p["imported_at"], reverse=True)
def get_module_overview():
    """Regroupe les tests du DERNIER import par module (group_path)."""
    conn = get_connection()

    latest = conn.execute("SELECT id, imported_at FROM imports ORDER BY id DESC LIMIT 1").fetchone()
    if not latest:
        conn.close()
        return []

    rows = conn.execute(
        "SELECT group_path, status FROM test_cases WHERE import_id = ?",
        (latest["id"],),
    ).fetchall()
    conn.close()

    modules = {}
    for r in rows:
        group = r["group_path"]
        modules.setdefault(group, {"PASS": 0, "FAIL": 0})
        modules[group][r["status"]] = modules[group].get(r["status"], 0) + 1

    result = []
    for group, data in modules.items():
        total = data["PASS"] + data["FAIL"]
        overall = "FAILED" if data["FAIL"] > 0 else "PASSED"
        result.append({
            "module": group.split("/")[-1],
            "full_path": group,
            "last_execution": latest["imported_at"][:16],
            "total": total,
            "overall": overall,
        })

    return sorted(result, key=lambda m: m["module"])
import statistics

def detect_anomalies():
    """Détecte les modules dont le dernier taux d'échec est anormalement élevé
    par rapport à leur historique (moyenne + 2 écarts-types)."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT i.imported_at, tc.group_path, tc.status
        FROM test_cases tc
        JOIN imports i ON tc.import_id = i.id
        ORDER BY i.imported_at ASC
    """).fetchall()
    conn.close()

    # Organise : { groupe: { date: {"PASS": x, "FAIL": y} } }
    by_group = {}
    for r in rows:
        g, d, s = r["group_path"], r["imported_at"], r["status"]
        by_group.setdefault(g, {})
        by_group[g].setdefault(d, {"PASS": 0, "FAIL": 0})
        by_group[g][d][s] = by_group[g][d].get(s, 0) + 1

    anomalies = []
    for group, dates_data in by_group.items():
        rates = []
        for date in sorted(dates_data.keys()):
            total = dates_data[date]["PASS"] + dates_data[date]["FAIL"]
            rate = (dates_data[date]["FAIL"] / total * 100) if total else 0
            rates.append(rate)

        # Besoin d'au moins 3 points pour calculer une moyenne/écart-type utile
        if len(rates) < 3:
            continue

        history = rates[:-1]   # tout sauf le dernier
        latest = rates[-1]     # le taux d'échec le plus récent

        mean = statistics.mean(history)
        stdev = statistics.stdev(history) if len(history) > 1 else 0
        threshold = mean + 2 * stdev

        if latest > threshold and latest > mean + 5:  # +5 évite le bruit sur de petites variations
            anomalies.append({
                "module": group.split("/")[-1],
                "full_path": group,
                "latest_rate": round(latest, 1),
                "average_rate": round(mean, 1),
            })

    return anomalies
def answer_question(question):
    """Chatbot simple à base de mots-clés qui interroge la base SQLite."""
    q = question.lower()
    conn = get_connection()

    latest = conn.execute("SELECT id, imported_at FROM imports ORDER BY id DESC LIMIT 1").fetchone()
    if not latest:
        conn.close()
        return "No data imported yet. Please import a report first."

    import_id = latest["id"]

    # Le module avec le plus d'échecs
    if "most failures" in q or "worst module" in q or "which module" in q:
        row = conn.execute("""
            SELECT group_path, COUNT(*) as fails
            FROM test_cases
            WHERE import_id = ? AND status = 'FAIL'
            GROUP BY group_path
            ORDER BY fails DESC LIMIT 1
        """, (import_id,)).fetchone()
        conn.close()
        if row:
            return f"The module with the most failures is **{row['group_path'].split('/')[-1]}** with {row['fails']} failed test(s)."
        return "No failures found in the latest import."

    # Taux de réussite global
    if "pass rate" in q or "success rate" in q:
        counts = conn.execute("""
            SELECT status, COUNT(*) as c FROM test_cases WHERE import_id = ? GROUP BY status
        """, (import_id,)).fetchall()
        conn.close()
        counts_dict = {r["status"]: r["c"] for r in counts}
        total = sum(counts_dict.values())
        passed = counts_dict.get("PASS", 0)
        rate = round(passed / total * 100, 1) if total else 0
        return f"The current pass rate is **{rate}%** ({passed} out of {total} tests passed)."

    # Nombre total de tests
    if "how many tests" in q or "total tests" in q:
        row = conn.execute("SELECT COUNT(*) as c FROM test_cases WHERE import_id = ?", (import_id,)).fetchone()
        conn.close()
        return f"There are **{row['c']}** tests in the latest import."

    # Nombre d'échecs
    if "how many failures" in q or "how many failed" in q:
        row = conn.execute("SELECT COUNT(*) as c FROM test_cases WHERE import_id = ? AND status='FAIL'", (import_id,)).fetchone()
        conn.close()
        return f"There are **{row['c']}** failed tests in the latest import."

    # Cause d'échec la plus fréquente (texte brut, approximatif)
    if "common" in q or "top failure" in q or "main cause" in q:
        row = conn.execute("""
            SELECT fails_text, COUNT(*) as c FROM test_cases
            WHERE import_id = ? AND status='FAIL' AND fails_text != ''
            GROUP BY fails_text ORDER BY c DESC LIMIT 1
        """, (import_id,)).fetchone()
        conn.close()
        if row:
            return f"The most common failure message appears {row['c']} time(s):\n\n*{row['fails_text'][:200]}...*"
        return "No failure details available."

    conn.close()
    return ("I can answer questions like:\n"
            "- Which module has the most failures?\n"
            "- What is the pass rate?\n"
            "- How many tests are there?\n"
            "- How many tests failed?\n"
            "- What is the most common failure?")

def get_import_list():
    """Renvoie la liste des imports disponibles pour les menus déroulants."""
    conn = get_connection()
    rows = conn.execute("SELECT id, imported_at, filenames FROM imports ORDER BY id DESC").fetchall()
    conn.close()
    result = []
    for r in rows:
        filenames = json.loads(r["filenames"])
        label = f"{r['imported_at'][:16]} — {', '.join(filenames) if filenames else 'empty'}"
        result.append({"id": r["id"], "label": label})
    return result


def compare_imports(import_id_a, import_id_b):
    """Compare deux imports : renvoie les tests fixed / regressed / unchanged / new / removed."""
    conn = get_connection()

    rows_a = conn.execute("SELECT test_case_id, name, group_path, status FROM test_cases WHERE import_id = ?", (import_id_a,)).fetchall()
    rows_b = conn.execute("SELECT test_case_id, name, group_path, status FROM test_cases WHERE import_id = ?", (import_id_b,)).fetchall()
    conn.close()

    map_a = {r["test_case_id"]: dict(r) for r in rows_a}
    map_b = {r["test_case_id"]: dict(r) for r in rows_b}

    fixed, regressed, unchanged = [], [], []

    common_ids = set(map_a.keys()) & set(map_b.keys())
    for tcid in common_ids:
        status_a = map_a[tcid]["status"]
        status_b = map_b[tcid]["status"]
        entry = {
            "id": tcid,
            "name": map_b[tcid]["name"],
            "group": map_b[tcid]["group_path"],
            "before": status_a,
            "after": status_b,
        }
        if status_a == "FAIL" and status_b == "PASS":
            fixed.append(entry)
        elif status_a == "PASS" and status_b == "FAIL":
            regressed.append(entry)
        else:
            unchanged.append(entry)

    return {
        "fixed": fixed,
        "regressed": regressed,
        "unchanged": unchanged,
        "total_common": len(common_ids),
    }        
