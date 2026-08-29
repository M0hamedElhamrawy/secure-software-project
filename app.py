import os
import sqlite3
from datetime import datetime, timezone
from functools import wraps

from flask import (
    Flask, request, session, redirect, url_for,
    render_template, g, abort, Response
)
from markupsafe import Markup
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "application.db")
MATERIALS_DIR = os.path.join(DATA_DIR, "materials")
PRIVATE_DIR = os.path.join(DATA_DIR, "private")

app = Flask(__name__)
app.config["SECRET_KEY"] = "f8f7c1e6a9b34d2e8c6a1f0d9b7e4c3a2d1e0f9c8b7a6d5e4f3c2b1a0d9e8f7"


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(MATERIALS_DIR, exist_ok=True)
    os.makedirs(PRIVATE_DIR, exist_ok=True)

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            bio TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            title TEXT NOT NULL,
            instructor TEXT NOT NULL,
            department TEXT NOT NULL,
            description TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            label TEXT NOT NULL,
            FOREIGN KEY (course_id) REFERENCES courses (id)
        );

        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_id INTEGER,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (course_id) REFERENCES courses (id)
        );
        """
    )
    db.commit()

    seed_data(db)
    db.close()


def seed_data(db):
    user_count = db.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    if user_count == 0:
        now = datetime.now(timezone.utc).isoformat()
        seed_users = [
            ("Portal Admin", "admin@example.local", "Admin123!", "admin", "Portal administrator."),
            ("Sam Student", "student@example.local", "Student123!", "user", "Third-year Computer Science student."),
            ("Alice Nguyen", "alice.nguyen@example.local", "Alice123!", "user", "Enjoys databases and hiking."),
            ("Ben Carter", "ben.carter@example.local", "Ben12345!", "user", "TA for Data Structures."),
            ("Carla Diaz", "carla.diaz@example.local", "Carla123!", "user", "Studying Secure Software Engineering."),
        ]
        for name, email, password, role, bio in seed_users:
            db.execute(
                "INSERT INTO users (name, email, password_hash, role, bio, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (name, email, generate_password_hash(password), role, bio, now),
            )
        db.commit()

    course_count = db.execute("SELECT COUNT(*) AS c FROM courses").fetchone()["c"]
    if course_count == 0:
        seed_courses = [
            ("CS101", "Introduction to Programming", "Dr. Emily Hart", "Computer Science",
             "Fundamentals of programming using Python: variables, control flow, functions, and basic data structures."),
            ("CS201", "Data Structures", "Dr. Michael Owens", "Computer Science",
             "A study of core data structures including lists, stacks, queues, trees, and hash tables."),
            ("SEC301", "Secure Software Engineering", "Dr. Priya Nair", "Computer Science",
             "Principles of building and evaluating secure applications, covering common vulnerability classes."),
            ("MATH210", "Discrete Mathematics", "Dr. Alan Reyes", "Mathematics",
             "Logic, set theory, combinatorics, and graph theory for computer science majors."),
        ]
        for code, title, instructor, department, description in seed_courses:
            db.execute(
                "INSERT INTO courses (code, title, instructor, department, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (code, title, instructor, department, description),
            )
        db.commit()

        materials = [
            ("CS101", "cs101_syllabus.txt", "Course Syllabus"),
            ("CS101", "cs101_week1_notes.txt", "Week 1 Lecture Notes"),
            ("CS201", "cs201_syllabus.txt", "Course Syllabus"),
            ("SEC301", "sec301_syllabus.txt", "Course Syllabus"),
            ("MATH210", "math210_syllabus.txt", "Course Syllabus"),
        ]
        code_to_id = {
            row["code"]: row["id"]
            for row in db.execute("SELECT id, code FROM courses").fetchall()
        }
        for code, filename, label in materials:
            db.execute(
                "INSERT INTO materials (course_id, filename, label) VALUES (?, ?, ?)",
                (code_to_id[code], filename, label),
            )
            file_path = os.path.join(MATERIALS_DIR, filename)
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(f"{label} for {code}\n\nThis is placeholder course material text.\n")
        db.commit()

    private_note = os.path.join(PRIVATE_DIR, "staff_notes.txt")
    if not os.path.exists(private_note):
        with open(private_note, "w", encoding="utf-8") as f:
            f.write(
                "Internal staff notes\n"
                "---------------------\n"
                "Reminder: faculty meeting moved to Friday 2pm.\n"
                "Grading deadline for this semester is the last day of finals week.\n"
            )

    note_count = db.execute("SELECT COUNT(*) AS c FROM notes").fetchone()["c"]
    if note_count == 0:
        now = datetime.now(timezone.utc).isoformat()
        student = db.execute("SELECT id FROM users WHERE email = ?", ("student@example.local",)).fetchone()
        cs101 = db.execute("SELECT id FROM courses WHERE code = ?", ("CS101",)).fetchone()
        sec301 = db.execute("SELECT id FROM courses WHERE code = ?", ("SEC301",)).fetchone()
        db.execute(
            "INSERT INTO notes (user_id, course_id, title, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (student["id"], cs101["id"], "Loops recap",
             "Remember that a for-loop in Python iterates over an iterable, "
             "while a while-loop keeps running until its condition is false.", now),
        )
        db.execute(
            "INSERT INTO notes (user_id, course_id, title, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (student["id"], sec301["id"], "Threat modeling",
             "STRIDE is a useful mnemonic for categorizing threats during design review.", now),
        )
        db.commit()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.path))
        if session.get("role") != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def current_user():
    if not session.get("user_id"):
        return None
    return get_db().execute(
        "SELECT id, name, email, role, bio, created_at FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    db = get_db()
    courses = db.execute("SELECT * FROM courses ORDER BY code").fetchall()
    return render_template("index.html", courses=courses)


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            error = "All fields are required."
        else:
            db = get_db()
            existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                error = "An account with that email already exists."
            else:
                db.execute(
                    "INSERT INTO users (name, email, password_hash, role, bio, created_at) "
                    "VALUES (?, ?, ?, 'user', '', ?)",
                    (name, email, generate_password_hash(password), datetime.now(timezone.utc).isoformat()),
                )
                db.commit()
                return redirect(url_for("login"))
    return render_template("register.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["name"] = user["name"]
            next_url = request.args.get("next") or url_for("dashboard")
            return redirect(next_url)
        error = "Invalid email or password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Course catalog
# ---------------------------------------------------------------------------

@app.route("/courses")
def courses():
    db = get_db()
    all_courses = db.execute("SELECT * FROM courses ORDER BY code").fetchall()

    q = request.args.get("q", "")
    notice = None
    results = all_courses
    if q:
        needle = q.lower()
        results = [
            c for c in all_courses
            if needle in c["title"].lower() or needle in c["code"].lower()
        ]
        notice = Markup("Showing results for: " + q)

    return render_template("courses.html", courses=results, query=q, notice=notice)


@app.route("/courses/<int:course_id>")
@login_required
def course_detail(course_id):
    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    if not course:
        abort(404)
    materials = db.execute(
        "SELECT * FROM materials WHERE course_id = ?", (course_id,)
    ).fetchall()
    return render_template("course_detail.html", course=course, materials=materials)


@app.route("/materials/download")
@login_required
def download_material():
    filename = request.args.get("file", "")
    if not filename:
        abort(400)

    file_path = os.path.join(MATERIALS_DIR, filename)
    if not os.path.isfile(file_path):
        abort(404)

    with open(file_path, "rb") as f:
        data = f.read()

    return Response(
        data,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename={os.path.basename(filename)}"},
    )


# ---------------------------------------------------------------------------
# Classmate directory
# ---------------------------------------------------------------------------

@app.route("/directory")
@login_required
def directory():
    name = request.args.get("name", "")
    results = []
    if name:
        db = get_db()
        query = "SELECT id, name, email, role, bio FROM users WHERE name LIKE '%" + name + "%'"
        results = db.execute(query).fetchall()
    return render_template("directory.html", results=results, name=name)


# ---------------------------------------------------------------------------
# Authenticated user area
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    notes = db.execute(
        "SELECT notes.*, courses.code AS course_code FROM notes "
        "LEFT JOIN courses ON notes.course_id = courses.id "
        "WHERE notes.user_id = ? ORDER BY notes.created_at DESC",
        (session["user_id"],),
    ).fetchall()
    course_list = db.execute("SELECT id, code, title FROM courses ORDER BY code").fetchall()
    return render_template("dashboard.html", notes=notes, courses=course_list)


@app.route("/notes/create", methods=["POST"])
@login_required
def create_note():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    course_id = request.form.get("course_id") or None

    if title and content:
        db = get_db()
        db.execute(
            "INSERT INTO notes (user_id, course_id, title, content, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (session["user_id"], course_id, title, content, datetime.now(timezone.utc).isoformat()),
        )
        db.commit()
    return redirect(url_for("dashboard"))


@app.route("/notes/<int:note_id>/delete", methods=["POST"])
@login_required
def delete_own_note(note_id):
    db = get_db()
    note = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if note and note["user_id"] == session["user_id"]:
        db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        db.commit()
    return redirect(url_for("dashboard"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    if request.method == "POST":
        bio = request.form.get("bio", "").strip()
        db.execute("UPDATE users SET bio = ? WHERE id = ?", (bio, session["user_id"]))
        db.commit()
    user = db.execute(
        "SELECT id, name, email, role, bio, created_at FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    return render_template("profile.html", user=user)


# ---------------------------------------------------------------------------
# Admin area
# ---------------------------------------------------------------------------

@app.route("/admin")
@admin_required
def admin():
    db = get_db()
    users = db.execute(
        "SELECT id, name, email, role, created_at FROM users ORDER BY created_at"
    ).fetchall()
    notes = db.execute(
        "SELECT notes.*, users.name AS author_name FROM notes "
        "JOIN users ON notes.user_id = users.id ORDER BY notes.created_at DESC"
    ).fetchall()
    return render_template("admin.html", users=users, notes=notes)


@app.route("/admin/notes/<int:note_id>/delete", methods=["POST"])
@admin_required
def admin_delete_note(note_id):
    db = get_db()
    db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    db.commit()
    return redirect(url_for("admin"))


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False)
else:
    init_db()
