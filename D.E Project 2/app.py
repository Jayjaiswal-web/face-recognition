"""
app.py — Flask REST API for the Face Recognition Attendance System
Serves the frontend SPA and exposes JSON endpoints consumed by it.
"""

import os
from flask import Flask, request, jsonify, session, send_from_directory
from functools import wraps
from datetime import datetime
from database import DatabaseManager

app = Flask(__name__, static_folder="frontend", static_url_path="/static")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "attendance_secret_dev_fallback_2024")

db = DatabaseManager()

# ── Helpers ───────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({"error": "Unauthorized"}), 401
            if session.get("role") not in roles:
                return jsonify({"error": "Forbidden"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

def serialize_lecture(lec):
    return {
        "id": lec[0],
        "subject": lec[1],
        "class_name": lec[2],
        "day_of_week": lec[3],
        "start_time": lec[4][:5] if lec[4] else "",
        "end_time": lec[5][:5] if lec[5] else "",
    }

def serialize_session(s):
    return {
        "lecture_id": s[0],
        "subject": s[1],
        "class_name": s[2],
        "day_of_week": s[3],
        "start_time": s[4][:5] if s[4] else "",
        "end_time": s[5][:5] if s[5] else "",
        "started_at": str(s[6]),
    }

# ── SPA entry point ───────────────────────────────────────────────────────────

@app.route("/")
def index():
    # Serve the SPA entry point using an absolute path
    return send_from_directory(os.path.join(app.root_path, "frontend"), "index.html")

# Fallback for any unknown route – serves the SPA so client‑side routing works
@app.errorhandler(404)
def not_found(e):
    return send_from_directory(os.path.join(app.root_path, "frontend"), "index.html")

# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    result = db.authenticate(username, password)
    if result:
        user_id, name, role = result
        session["user_id"] = user_id
        session["name"] = name
        session["role"] = role
        return jsonify({"id": user_id, "name": name, "role": role})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})

@app.route("/api/me")
def me():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify({
        "id": session["user_id"],
        "name": session["name"],
        "role": session["role"],
    })

# ── Dashboard Stats ───────────────────────────────────────────────────────────

@app.route("/api/dashboard")
@login_required
def dashboard():
    role = session["role"]
    
    if role == "admin":
        users = db.get_all_users()
        classes = db.get_all_classes()
        lectures = db.get_all_lectures()
        active = db.get_active_sessions()
        return jsonify({
            "total_users": len(users),
            "total_classes": len(classes),
            "total_lectures": len(lectures),
            "active_sessions": len(active),
        })
    
    elif role == "teacher":
        lectures = db.get_all_lectures()
        active = db.get_active_sessions()
        return jsonify({
            "total_lectures": len(lectures),
            "active_sessions": len(active),
        })
    
    else:  # student
        return jsonify({"message": "Welcome!"})

# ── Classes ───────────────────────────────────────────────────────────────────

@app.route("/api/classes", methods=["GET"])
def get_classes():
    classes = db.get_all_classes()
    return jsonify([{"id": c[0], "name": c[1]} for c in classes])

@app.route("/api/classes", methods=["POST"])
@role_required("admin")
def add_class():
    data = request.get_json()
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Class name required"}), 400
    class_id = db.add_class(name)
    if class_id:
        return jsonify({"id": class_id, "name": name}), 201
    return jsonify({"error": "Failed to create class"}), 500

# ── Users ─────────────────────────────────────────────────────────────────────

@app.route("/api/users", methods=["GET"])
@role_required("admin")
def get_users():
    users = db.get_all_users()
    return jsonify([
        {"id": u[0], "name": u[1], "role": u[2], "username": u[3], "class_name": u[4]}
        for u in users
    ])

@app.route("/api/users", methods=["POST"])
@role_required("admin")
def add_user():
    data = request.get_json()
    name = data.get("name", "").strip()
    role = data.get("role", "student")
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    class_id = data.get("class_id")

    if not name or not username or not password:
        return jsonify({"error": "name, username, and password are required"}), 400

    user_id = db.add_user(name, role, username, password, class_id or None)
    if user_id:
        return jsonify({"id": user_id, "name": name, "role": role}), 201
    return jsonify({"error": "Failed to create user (username may already exist)"}), 500

@app.route("/api/register", methods=["POST"])
def register():
    # Handle multipart/form-data
    data = request.form
    name = data.get("name", "").strip()
    role = data.get("role", "student").lower()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    class_id = data.get("class_id")

    if role not in ["admin", "student"]:
        return jsonify({"error": "Invalid role. Only admin and student are allowed."}), 400

    if not name or not username or not password:
        return jsonify({"error": "name, username, and password are required"}), 400

    face_image = request.files.get("face_image")
    if role == "student" and not face_image:
        return jsonify({"error": "Face photo is required for students"}), 400

    user_id = db.add_user(name, role, username, password, class_id or None)
    if user_id:
        if role == "student" and face_image:
            # Format: id_name_count.jpg (as required by simple_cam.py)
            filename = f"{user_id}_{name.replace(' ', '')}_1.jpg"
            faces_dir = "faces"
            if not os.path.exists(faces_dir):
                os.makedirs(faces_dir)
            filepath = os.path.join(faces_dir, filename)
            face_image.save(filepath)
            # Upload to Supabase Storage
            db.upload_face(filepath)
            
        return jsonify({"id": user_id, "name": name, "role": role}), 201
    return jsonify({"error": "Registration failed (username may already exist)"}), 500

# ── Lectures ──────────────────────────────────────────────────────────────────

@app.route("/api/lectures", methods=["GET"])
@login_required
def get_lectures():
    lectures = db.get_all_lectures()
    return jsonify([serialize_lecture(l) for l in lectures])

@app.route("/api/lectures", methods=["POST"])
@role_required("admin", "teacher")
def add_lecture():
    data = request.get_json()
    subject = data.get("subject", "").strip()
    class_id = data.get("class_id")
    day = data.get("day_of_week", "").strip()
    start = data.get("start_time", "").strip()
    end = data.get("end_time", "").strip()

    if not all([subject, class_id, day, start, end]):
        return jsonify({"error": "All fields required"}), 400

    ok = db.add_lecture(subject, class_id, day, start, end)
    if ok:
        return jsonify({"ok": True}), 201
    return jsonify({"error": "Failed to add lecture"}), 500

# ── Sessions ──────────────────────────────────────────────────────────────────

@app.route("/api/sessions/active", methods=["GET"])
@login_required
def get_active_sessions():
    sessions = db.get_active_sessions()
    return jsonify([serialize_session(s) for s in sessions])

@app.route("/api/sessions/start", methods=["POST"])
@role_required("admin", "teacher")
def start_session():
    data = request.get_json()
    lecture_id = data.get("lecture_id")
    if not lecture_id:
        return jsonify({"error": "lecture_id required"}), 400
    ok = db.start_session(lecture_id)
    if ok:
        return jsonify({"ok": True})
    return jsonify({"error": "Failed to start session"}), 500

@app.route("/api/sessions/end", methods=["POST"])
@role_required("admin", "teacher")
def end_session():
    data = request.get_json()
    lecture_id = data.get("lecture_id")
    if not lecture_id:
        return jsonify({"error": "lecture_id required"}), 400
    db.end_session(lecture_id)
    return jsonify({"ok": True})

# ── Attendance ────────────────────────────────────────────────────────────────

@app.route("/api/attendance", methods=["GET"])
@login_required
def get_attendance():
    lecture_id = request.args.get("lecture_id")
    date = request.args.get("date")  # optional, defaults to today
    if not lecture_id:
        return jsonify({"error": "lecture_id required"}), 400
    records = db.get_attendance_by_lecture(lecture_id, date)
    return jsonify([
        {"name": r[0], "time": str(r[1]), "user_id": r[2]}
        for r in records
    ])

@app.route("/api/attendance/summary", methods=["GET"])
@role_required("admin", "teacher")
def attendance_summary():
    """Return per-lecture attendance counts for today."""
    lectures = db.get_all_lectures()
    today = datetime.now().strftime("%Y-%m-%d")
    summary = []
    for lec in lectures:
        records = db.get_attendance_by_lecture(lec[0], today)
        summary.append({
            "lecture_id": lec[0],
            "subject": lec[1],
            "class_name": lec[2],
            "day_of_week": lec[3],
            "count": len(records),
        })
    return jsonify(summary)

@app.route("/api/my-attendance", methods=["GET"])
@login_required
def my_attendance():
    """Return the logged-in student's full attendance history."""
    user_id = session["user_id"]
    records = db.get_attendance_by_user(user_id)
    # Also calculate per-lecture totals so student can see percentage
    lectures = db.get_all_lectures()
    lecture_map = {l[0]: l for l in lectures}  # id -> tuple

    # Group by lecture_id
    from collections import defaultdict
    grouped = defaultdict(list)
    for r in records:
        grouped[r["lecture_id"]].append(r)

    # Build summary per lecture that has any record
    summary = []
    for lid, recs in grouped.items():
        summary.append({
            "lecture_id": lid,
            "subject": recs[0]["subject"],
            "class_name": recs[0]["class_name"],
            "day_of_week": recs[0]["day_of_week"],
            "start_time": recs[0]["start_time"],
            "end_time": recs[0]["end_time"],
            "sessions_attended": len(recs),
            "records": recs,
        })

    return jsonify({
        "total_present": len(records),
        "unique_lectures": len(summary),
        "summary": sorted(summary, key=lambda x: x["subject"]),
        "all_records": records,
    })

@app.route("/api/all-attendance", methods=["GET"])
@role_required("admin", "teacher")
def all_attendance():
    """Admin: get full attendance for all users for a specific lecture or all lectures today."""
    from collections import defaultdict
    lecture_id = request.args.get("lecture_id")
    date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    if lecture_id:
        records = db.get_attendance_by_lecture(lecture_id, date)
        return jsonify([{"name": r[0], "time": str(r[1]), "user_id": r[2]} for r in records])

    # All lectures, today
    lectures = db.get_all_lectures()
    result = []
    for lec in lectures:
        recs = db.get_attendance_by_lecture(lec[0], date)
        if recs:
            result.append({
                "lecture_id": lec[0],
                "subject": lec[1],
                "class_name": lec[2],
                "records": [{"name": r[0], "time": str(r[1])} for r in recs]
            })
    return jsonify(result)

# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=4000)
