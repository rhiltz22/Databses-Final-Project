"""
CS 5330 Group Project — Flask Backend
Social Media Analysis Database

Reads DB credentials from db_config.json (same directory as this file).
Run:  python app.py
API:  http://localhost:5000
"""

import json
import os
from datetime import datetime, date

import mysql.connector
from flask import Flask, jsonify, request
from flask_cors import CORS

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
CORS(app)  # allow the frontend (any origin) to reach us during development

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "db_config.json")

with open(CONFIG_PATH) as f:
    DB_CONFIG = json.load(f)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_conn():
    """Return a new MySQL connection using the config file."""
    return mysql.connector.connect(**DB_CONFIG)


def query(sql, params=(), one=False, commit=False):
    """
    Run *sql* with *params*.
    - commit=True  → INSERT / UPDATE / DELETE; returns lastrowid.
    - one=True     → SELECT returning a single dict or None.
    - default      → SELECT returning a list of dicts.
    """
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        if commit:
            conn.commit()
            return cur.lastrowid
        rows = cur.fetchall()
        return rows[0] if (one and rows) else (None if one else rows)
    finally:
        cur.close()
        conn.close()


def error(msg, status=400):
    return jsonify({"error": msg}), status


def serialize(obj):
    """Make date/datetime JSON-serialisable."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return obj


def serialize_row(row):
    return {k: serialize(v) for k, v in row.items()} if row else None


def serialize_rows(rows):
    return [serialize_row(r) for r in rows]


# ---------------------------------------------------------------------------
# Institutions
# ---------------------------------------------------------------------------

@app.route("/api/institutions", methods=["GET"])
def list_institutions():
    return jsonify(serialize_rows(query("SELECT * FROM Institution ORDER BY institution_name")))


@app.route("/api/institutions", methods=["POST"])
def create_institution():
    data = request.get_json()
    name = (data or {}).get("institution_name", "").strip()
    if not name:
        return error("institution_name is required")
    query("INSERT IGNORE INTO Institution (institution_name) VALUES (%s)", (name,), commit=True)
    return jsonify({"institution_name": name}), 201


# ---------------------------------------------------------------------------
# Platforms
# ---------------------------------------------------------------------------

@app.route("/api/platforms", methods=["GET"])
def list_platforms():
    return jsonify(serialize_rows(query("SELECT * FROM Platform ORDER BY platform_name")))


@app.route("/api/platforms", methods=["POST"])
def create_platform():
    data = request.get_json()
    name = (data or {}).get("platform_name", "").strip()
    if not name:
        return error("platform_name is required")
    query("INSERT IGNORE INTO Platform (platform_name) VALUES (%s)", (name,), commit=True)
    return jsonify({"platform_name": name}), 201


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@app.route("/api/projects", methods=["POST"])
def create_project():
    data = request.get_json() or {}
    project_name = data.get("project_name", "").strip()
    institution_name = data.get("institution_name", "").strip()
    if not project_name or not institution_name:
        return error("project_name and institution_name are required")

    start_date = data.get("start_date") or None
    end_date = data.get("end_date") or None
    if start_date and end_date and end_date < start_date:
        return error("end_date must be on or after start_date")

    # Ensure institution exists
    query("INSERT IGNORE INTO Institution (institution_name) VALUES (%s)",
          (institution_name,), commit=True)

    try:
        query(
            """INSERT INTO Project
               (project_name, manager_first_name, manager_last_name,
                start_date, end_date, institution_name)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (project_name,
             data.get("manager_first_name") or None,
             data.get("manager_last_name") or None,
             start_date, end_date, institution_name),
            commit=True,
        )
    except mysql.connector.IntegrityError:
        return error(f"Project '{project_name}' already exists", 409)

    # Insert field definitions
    fields = [f.strip() for f in data.get("fields", []) if f.strip()]
    for field_name in fields:
        query(
            "INSERT IGNORE INTO Field (field_name, project_name) VALUES (%s, %s)",
            (field_name, project_name), commit=True,
        )

    return jsonify({"project_name": project_name, "fields_created": fields}), 201


@app.route("/api/projects", methods=["GET"])
def list_projects():
    rows = query("SELECT * FROM Project ORDER BY project_name")
    return jsonify(serialize_rows(rows))


@app.route("/api/projects/<project_name>/fields", methods=["GET"])
def list_fields(project_name):
    rows = query(
        "SELECT field_name FROM Field WHERE project_name = %s ORDER BY field_name",
        (project_name,)
    )
    return jsonify([r["field_name"] for r in rows])


@app.route("/api/projects/<project_name>/fields", methods=["POST"])
def add_field(project_name):
    data = request.get_json() or {}
    field_name = data.get("field_name", "").strip()
    if not field_name:
        return error("field_name is required")
    existing = query("SELECT * FROM Project WHERE project_name = %s", (project_name,), one=True)
    if not existing:
        return error(f"Project '{project_name}' not found", 404)
    query("INSERT IGNORE INTO Field (field_name, project_name) VALUES (%s, %s)",
          (field_name, project_name), commit=True)
    return jsonify({"field_name": field_name, "project_name": project_name}), 201


# ---------------------------------------------------------------------------
# UserAccounts
# ---------------------------------------------------------------------------

@app.route("/api/accounts", methods=["POST"])
def create_account():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    platform_name = data.get("platform_name", "").strip()
    if not username or not platform_name:
        return error("username and platform_name are required")
    if len(username) > 40:
        return error("username must be at most 40 characters")

    # Ensure platform exists
    query("INSERT IGNORE INTO Platform (platform_name) VALUES (%s)", (platform_name,), commit=True)

    query(
        """INSERT IGNORE INTO UserAccount
           (username, platform_name, unique_id, first_name, last_name,
            country_of_birth, country_of_residence, age, gender, verification_status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (username, platform_name,
         data.get("unique_id") or None,
         data.get("first_name") or None,
         data.get("last_name") or None,
         data.get("country_of_birth") or None,
         data.get("country_of_residence") or None,
         data.get("age") or None,
         data.get("gender") or None,
         bool(data.get("verification_status", False))),
        commit=True,
    )
    return jsonify({"username": username, "platform_name": platform_name}), 201


# ---------------------------------------------------------------------------
# Persons & account linking
# ---------------------------------------------------------------------------

@app.route("/api/persons", methods=["POST"])
def create_person():
    data = request.get_json() or {}
    pid = query(
        "INSERT INTO Person (first_name, last_name) VALUES (%s, %s)",
        (data.get("first_name") or None, data.get("last_name") or None),
        commit=True,
    )
    return jsonify({"unique_id": pid}), 201


@app.route("/api/persons/link", methods=["POST"])
def link_accounts():
    """
    Link one or more (platform, username) pairs to a single Person.
    If unique_id is omitted, a new Person row is created automatically.
    """
    data = request.get_json() or {}
    accounts = data.get("accounts", [])
    if not accounts:
        return error("accounts list is required")

    unique_id = data.get("unique_id")
    if unique_id:
        existing = query("SELECT * FROM Person WHERE unique_id = %s", (unique_id,), one=True)
        if not existing:
            return error(f"Person {unique_id} not found", 404)
    else:
        unique_id = query(
            "INSERT INTO Person (first_name, last_name) VALUES (%s, %s)",
            (data.get("first_name") or None, data.get("last_name") or None),
            commit=True,
        )

    linked = []
    errors = []
    for acc in accounts:
        uname = acc.get("username", "").strip()
        pname = acc.get("platform_name", "").strip()
        if not uname or not pname:
            errors.append(f"Skipped invalid entry: {acc}")
            continue

        # Ensure platform + account row exist
        query("INSERT IGNORE INTO Platform (platform_name) VALUES (%s)", (pname,), commit=True)
        query(
            "INSERT IGNORE INTO UserAccount (username, platform_name) VALUES (%s, %s)",
            (uname, pname), commit=True,
        )

        # Check if this account is already linked to a DIFFERENT person
        existing_link = query(
            "SELECT unique_id FROM UserAccount WHERE username = %s AND platform_name = %s",
            (uname, pname), one=True,
        )
        already_linked_to = existing_link.get("unique_id") if existing_link else None

        if already_linked_to is not None and already_linked_to != unique_id:
            errors.append(
                f"@{uname} on {pname} is already linked to person ID {already_linked_to} "
                f"— unlink them first before reassigning."
            )
            continue

        query(
            "UPDATE UserAccount SET unique_id = %s WHERE username = %s AND platform_name = %s",
            (unique_id, uname, pname), commit=True,
        )
        linked.append({"username": uname, "platform_name": pname})

    # If every account was blocked, roll back the auto-created Person row
    if not linked and not data.get("unique_id"):
        query("DELETE FROM Person WHERE unique_id = %s", (unique_id,), commit=True)
        return error(
            "No accounts were linked. All provided accounts are already linked to other people. "
            + " | ".join(errors),
            409,
        )

    return jsonify({
        "unique_id": unique_id,
        "linked": linked,
        "warnings": errors,
    }), 200


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------

@app.route("/api/posts", methods=["POST"])
def create_post():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    platform_name = data.get("platform_name", "").strip()
    text_content = data.get("text", "").strip()
    posted_at = data.get("time", "").strip()

    # Required field validation
    if not username or not platform_name or not text_content or not posted_at:
        return error("username, platform_name, text, and time are required")

    # Username length
    if len(username) > 40:
        return error("username must be at most 40 characters")

    # Validate likes / dislikes are non-negative integers
    num_likes = data.get("num_likes")
    num_dislikes = data.get("num_dislikes")
    if num_likes not in (None, "", 0):
        try:
            num_likes = int(num_likes)
            if num_likes < 0:
                return error("num_likes must be a non-negative integer")
        except (ValueError, TypeError):
            return error("num_likes must be a non-negative integer")
    else:
        num_likes = None

    if num_dislikes not in (None, "", 0):
        try:
            num_dislikes = int(num_dislikes)
            if num_dislikes < 0:
                return error("num_dislikes must be a non-negative integer")
        except (ValueError, TypeError):
            return error("num_dislikes must be a non-negative integer")
    else:
        num_dislikes = None

    # Validate repost_of is a positive integer if provided
    repost_of = data.get("repost_of") or None
    if repost_of:
        try:
            repost_of = int(repost_of)
            if repost_of <= 0:
                return error("repost_of must be a positive post ID")
            # Check the referenced post actually exists
            exists = query("SELECT post_id FROM Post WHERE post_id = %s", (repost_of,), one=True)
            if not exists:
                return error(f"Repost target post ID {repost_of} does not exist", 404)
        except (ValueError, TypeError):
            return error("repost_of must be a valid post ID integer")

    # Ensure platform + account exist
    query("INSERT IGNORE INTO Platform (platform_name) VALUES (%s)", (platform_name,), commit=True)
    query(
        "INSERT IGNORE INTO UserAccount (username, platform_name) VALUES (%s, %s)",
        (username, platform_name), commit=True,
    )

    try:
        post_id = query(
            """INSERT INTO Post
               (username, platform_name, posted_at, text_content,
                city, state, country, num_likes, num_dislikes,
                contains_multimedia, repost_of_post_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (username, platform_name, posted_at, text_content,
             data.get("city") or None,
             data.get("state") or None,
             data.get("country") or None,
             num_likes,
             num_dislikes,
             {"yes": True, "no": False}.get(data.get("contains_multimedia", ""), None),
             repost_of),
            commit=True,
        )
    except mysql.connector.IntegrityError as e:
        msg = str(e)
        if "uq_post_time" in msg:
            return error("This user already has a post on that platform at that exact time.", 409)
        return error(msg, 409)
    except mysql.connector.DataError as e:
        return error(f"Invalid data: {str(e)}", 400)
    except Exception as e:
        return error(f"Unexpected error: {str(e)}", 500)

    project_name = data.get("project_name", "").strip()
    return jsonify({"post_id": post_id, "project_name": project_name or None}), 201


@app.route("/api/posts", methods=["GET"])
def query_posts():
    """
    Query posts with optional AND filters:
      platform, username, first_name, last_name, from, to
    Returns posts with their associated project names.
    """
    args = request.args
    conditions = []
    params = []

    if args.get("platform"):
        conditions.append("p.platform_name = %s")
        params.append(args["platform"])

    if args.get("username"):
        conditions.append("p.username = %s")
        params.append(args["username"])

    if args.get("first_name"):
        conditions.append("ua.first_name = %s")
        params.append(args["first_name"])

    if args.get("last_name"):
        conditions.append("ua.last_name = %s")
        params.append(args["last_name"])

    if args.get("from"):
        conditions.append("p.posted_at >= %s")
        params.append(args["from"])

    if args.get("to"):
        conditions.append("p.posted_at <= %s")
        params.append(args["to"])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    posts = query(
        f"""SELECT p.post_id, p.username, p.platform_name, p.posted_at,
                   p.text_content, p.city, p.state, p.country,
                   p.num_likes, p.num_dislikes, p.contains_multimedia,
                   p.repost_of_post_id,
                   ua.first_name, ua.last_name
            FROM Post p
            JOIN UserAccount ua ON ua.username = p.username
                               AND ua.platform_name = p.platform_name
            {where}
            ORDER BY p.posted_at DESC
            LIMIT 500""",
        params,
    )

    # Fetch associated project names for each post
    post_ids = [r["post_id"] for r in posts]
    experiments_map = {}
    if post_ids:
        fmt = ",".join(["%s"] * len(post_ids))
        exp_rows = query(
            f"SELECT DISTINCT post_id, project_name FROM AnalysisResult WHERE post_id IN ({fmt})",
            post_ids,
        )
        for r in exp_rows:
            experiments_map.setdefault(r["post_id"], []).append(r["project_name"])

    result = []
    for row in posts:
        r = serialize_row(row)
        r["experiments"] = experiments_map.get(row["post_id"], [])
        result.append(r)

    return jsonify(result)


# ---------------------------------------------------------------------------
# Analysis results
# ---------------------------------------------------------------------------

@app.route("/api/analysis", methods=["POST"])
def save_analysis():
    """
    Save (partial) analysis results for a post in a project.
    Body: { project_name, post_id, results: [{field_name, field_value}] }
    """
    data = request.get_json() or {}
    project_name = data.get("project_name", "").strip()
    post_id = data.get("post_id")
    results = data.get("results", [])

    if not project_name or not post_id:
        return error("project_name and post_id are required")

    project = query("SELECT * FROM Project WHERE project_name = %s", (project_name,), one=True)
    if not project:
        return error(f"Project '{project_name}' not found", 404)

    post = query("SELECT * FROM Post WHERE post_id = %s", (post_id,), one=True)
    if not post:
        return error(f"Post {post_id} not found", 404)

    saved = []
    skipped = []
    for item in results:
        field_name = item.get("field_name", "").strip()
        field_value = item.get("field_value", "")
        if not field_name:
            continue

        # Auto-create field if it doesn't exist yet
        query("INSERT IGNORE INTO Field (field_name, project_name) VALUES (%s, %s)",
              (field_name, project_name), commit=True)

        query(
            """INSERT INTO AnalysisResult (project_name, post_id, field_name, field_value)
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE field_value = VALUES(field_value)""",
            (project_name, post_id, field_name, field_value or None),
            commit=True,
        )
        saved.append(field_name)

    return jsonify({"saved": saved, "skipped": skipped}), 200


# ---------------------------------------------------------------------------
# Experiment (project) query
# ---------------------------------------------------------------------------

@app.route("/api/experiments/<path:project_name>", methods=["GET"])
def query_experiment(project_name):
    """
    Return all posts associated with a project, their analysis results,
    and per-field coverage percentages.
    """
    project = query("SELECT * FROM Project WHERE project_name = %s", (project_name,), one=True)
    if not project:
        return error(f"Project '{project_name}' not found", 404)

    fields = query(
        "SELECT field_name FROM Field WHERE project_name = %s ORDER BY field_name",
        (project_name,)
    )
    field_names = [f["field_name"] for f in fields]

    # All posts that have at least one result in this project
    post_rows = query(
        """SELECT DISTINCT p.post_id, p.username, p.platform_name, p.posted_at, p.text_content
           FROM AnalysisResult ar
           JOIN Post p ON p.post_id = ar.post_id
           WHERE ar.project_name = %s
           ORDER BY p.posted_at DESC""",
        (project_name,)
    )

    # All results for this project
    result_rows = query(
        "SELECT post_id, field_name, field_value FROM AnalysisResult WHERE project_name = %s",
        (project_name,)
    )

    # Build per-post result map
    results_map = {}
    for r in result_rows:
        results_map.setdefault(r["post_id"], {})[r["field_name"]] = r["field_value"]

    total_posts = len(post_rows)
    coverage = {}
    for fn in field_names:
        filled = sum(
            1 for pid in results_map
            if results_map[pid].get(fn) is not None
        )
        coverage[fn] = round(filled / total_posts * 100, 1) if total_posts else 0.0

    posts_out = []
    for p in post_rows:
        row = serialize_row(p)
        row["results"] = results_map.get(p["post_id"], {})
        posts_out.append(row)

    return jsonify({
        "project": serialize_row(project),
        "fields": field_names,
        "coverage": coverage,
        "posts": posts_out,
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=False, port=5000)


# ---------------------------------------------------------------------------
# Global error handlers — ensures nothing ever hangs or leaks a stack trace
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(Exception)
def unhandled_exception(e):
    return jsonify({"error": "Unexpected error", "detail": str(e)}), 500
