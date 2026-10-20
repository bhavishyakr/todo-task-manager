"""
TaskFlow - Full-stack To-Do Task Manager
Backend: Python + Flask + SQLite   |   Frontend: HTML + CSS + JavaScript
"""
import os
import re
import sqlite3
from datetime import date, datetime
from functools import wraps

from flask import Flask, g, jsonify, render_template, request, session, redirect, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-in-production")
app.config["DATABASE"] = os.path.join(BASE_DIR, "taskflow.db")

PRIORITIES = ("low", "medium", "high")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ----------------------------------------------------------------- database
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title       TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            category    TEXT NOT NULL DEFAULT 'General',
            priority    TEXT NOT NULL DEFAULT 'medium',
            due_date    TEXT,
            completed   INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id);
        """
    )
    db.commit()


# --------------------------------------------------------------------- auth
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return jsonify(error="Please log in to continue."), 401
        return view(*args, **kwargs)
    return wrapped


def error(message, status=400):
    return jsonify(error=message), status


@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if len(name) < 2:
        return error("Enter your name (at least 2 characters).")
    if not EMAIL_RE.match(email):
        return error("Enter a valid email address.")
    if len(password) < 6:
        return error("Password must be at least 6 characters.")

    db = get_db()
    if db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        return error("An account with this email already exists.", 409)

    cur = db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash(password)),
    )
    db.commit()
    session["user_id"] = cur.lastrowid
    return jsonify(id=cur.lastrowid, name=name, email=email), 201


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user or not check_password_hash(user["password_hash"], password):
        return error("Email or password is incorrect.", 401)
    session["user_id"] = user["id"]
    return jsonify(id=user["id"], name=user["name"], email=user["email"])


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@app.get("/api/me")
@login_required
def me():
    user = get_db().execute(
        "SELECT id, name, email FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()
    if not user:
        session.clear()
        return error("Please log in to continue.", 401)
    return jsonify(dict(user))


# -------------------------------------------------------------------- tasks
def task_to_dict(row):
    d = dict(row)
    d["completed"] = bool(d["completed"])
    d["overdue"] = bool(
        d["due_date"] and not d["completed"] and d["due_date"] < date.today().isoformat()
    )
    return d


def validate_task(data, partial=False):
    """Return (clean_dict, error_message)."""
    clean = {}
    if not partial or "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            return None, "Task title is required."
        if len(title) > 120:
            return None, "Title must be 120 characters or fewer."
        clean["title"] = title
    if "description" in data:
        clean["description"] = (data.get("description") or "").strip()[:1000]
    if "category" in data:
        clean["category"] = (data.get("category") or "General").strip()[:30] or "General"
    if "priority" in data:
        if data["priority"] not in PRIORITIES:
            return None, "Priority must be low, medium or high."
        clean["priority"] = data["priority"]
    if "due_date" in data:
        due = data.get("due_date") or None
        if due:
            try:
                datetime.strptime(due, "%Y-%m-%d")
            except ValueError:
                return None, "Due date must look like YYYY-MM-DD."
        clean["due_date"] = due
    return clean, None


def own_task(task_id):
    return get_db().execute(
        "SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, session["user_id"])
    ).fetchone()


@app.get("/api/tasks")
@login_required
def list_tasks():
    status = request.args.get("status", "all")          # all | active | completed | overdue
    priority = request.args.get("priority", "all")
    category = request.args.get("category", "all")
    search = (request.args.get("search") or "").strip()
    sort = request.args.get("sort", "newest")

    sql = "SELECT * FROM tasks WHERE user_id = ?"
    params = [session["user_id"]]

    if status == "active":
        sql += " AND completed = 0"
    elif status == "completed":
        sql += " AND completed = 1"
    elif status == "overdue":
        sql += " AND completed = 0 AND due_date IS NOT NULL AND due_date < ?"
        params.append(date.today().isoformat())
    if priority in PRIORITIES:
        sql += " AND priority = ?"
        params.append(priority)
    if category != "all":
        sql += " AND category = ?"
        params.append(category)
    if search:
        sql += " AND (title LIKE ? OR description LIKE ?)"
        params += [f"%{search}%"] * 2

    order = {
        "newest": "id DESC",
        "oldest": "id ASC",
        "due": "due_date IS NULL, due_date ASC, id DESC",
        "priority": "CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC",
        "title": "title COLLATE NOCASE ASC",
    }.get(sort, "id DESC")
    sql += f" ORDER BY completed ASC, {order}"

    rows = get_db().execute(sql, params).fetchall()
    return jsonify([task_to_dict(r) for r in rows])


@app.post("/api/tasks")
@login_required
def create_task():
    data = request.get_json(silent=True) or {}
    clean, err = validate_task(data)
    if err:
        return error(err)
    db = get_db()
    cur = db.execute(
        """INSERT INTO tasks (user_id, title, description, category, priority, due_date)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            session["user_id"],
            clean["title"],
            clean.get("description", ""),
            clean.get("category", "General"),
            clean.get("priority", "medium"),
            clean.get("due_date"),
        ),
    )
    db.commit()
    return jsonify(task_to_dict(own_task(cur.lastrowid))), 201


@app.put("/api/tasks/<int:task_id>")
@login_required
def update_task(task_id):
    if not own_task(task_id):
        return error("Task not found.", 404)
    clean, err = validate_task(request.get_json(silent=True) or {}, partial=True)
    if err:
        return error(err)
    if clean:
        cols = ", ".join(f"{k} = ?" for k in clean)
        db = get_db()
        db.execute(f"UPDATE tasks SET {cols} WHERE id = ?", (*clean.values(), task_id))
        db.commit()
    return jsonify(task_to_dict(own_task(task_id)))


@app.patch("/api/tasks/<int:task_id>/toggle")
@login_required
def toggle_task(task_id):
    task = own_task(task_id)
    if not task:
        return error("Task not found.", 404)
    now_done = 0 if task["completed"] else 1
    db = get_db()
    db.execute(
        "UPDATE tasks SET completed = ?, completed_at = ? WHERE id = ?",
        (now_done, datetime.now().isoformat(timespec="seconds") if now_done else None, task_id),
    )
    db.commit()
    return jsonify(task_to_dict(own_task(task_id)))


@app.delete("/api/tasks/<int:task_id>")
@login_required
def delete_task(task_id):
    if not own_task(task_id):
        return error("Task not found.", 404)
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    return jsonify(ok=True)


@app.delete("/api/tasks/completed")
@login_required
def clear_completed():
    db = get_db()
    cur = db.execute(
        "DELETE FROM tasks WHERE user_id = ? AND completed = 1", (session["user_id"],)
    )
    db.commit()
    return jsonify(deleted=cur.rowcount)


@app.get("/api/stats")
@login_required
def stats():
    db = get_db()
    uid = session["user_id"]
    today = date.today().isoformat()
    row = db.execute(
        """SELECT COUNT(*) AS total,
                  COALESCE(SUM(completed), 0) AS completed,
                  COALESCE(SUM(CASE WHEN completed = 0 AND due_date < ? THEN 1 ELSE 0 END), 0) AS overdue,
                  COALESCE(SUM(CASE WHEN completed = 0 AND due_date = ? THEN 1 ELSE 0 END), 0) AS due_today
           FROM tasks WHERE user_id = ?""",
        (today, today, uid),
    ).fetchone()
    cats = [
        r["category"]
        for r in db.execute(
            "SELECT DISTINCT category FROM tasks WHERE user_id = ? ORDER BY category COLLATE NOCASE",
            (uid,),
        )
    ]
    total, done = row["total"], row["completed"]
    return jsonify(
        total=total,
        completed=done,
        active=total - done,
        overdue=row["overdue"],
        due_today=row["due_today"],
        percent=round(done / total * 100) if total else 0,
        categories=cats,
    )


# -------------------------------------------------------------------- pages
@app.get("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("auth_page"))
    return render_template("index.html")


@app.get("/auth")
def auth_page():
    if "user_id" in session:
        return redirect(url_for("index"))
    return render_template("auth.html")


with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)
