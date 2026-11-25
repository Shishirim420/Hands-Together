"""Page and JSON API routes for Hands Together."""

import hashlib
import hmac
import secrets
import sqlite3
from datetime import date, datetime

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, session, url_for

from .models import database

web = Blueprint("web", __name__)


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def json_error(message, status=400):
    return jsonify({"error": message}), status


def admin_api_guard():
    if session.get("account_type") != "Admin":
        return json_error("Administrator access is required.", 403)
    return None


@web.get("/")
@web.get("/home")
@web.get("/index.html")
def home():
    return render_template("index.html")


@web.get("/signup")
@web.get("/signup.html")
def signup_page():
    return render_template("signup.html")


@web.get("/login")
@web.get("/login.html")
def login_page():
    return render_template("login.html")


@web.get("/found")
@web.get("/found.html")
def found_page():
    return render_template("found.html")


@web.get("/missing-person")
def missing_person_page():
    return render_template("missing_person.html")


@web.get("/volunteer")
@web.get("/volunteer.html")
def volunteer_page():
    return render_template("volunteer.html")


@web.get("/donate")
def donate_page():
    return render_template("donate.html")


@web.get("/complaint")
def complaint_page():
    return render_template("complaint.html")


@web.get("/admin")
def admin_dashboard():
    if not session.get("user_id"):
        return redirect(url_for("web.login_page"))
    if session.get("account_type") != "Admin":
        abort(403)
    with database() as db:
        counts = {
            "reports": db.execute("SELECT COUNT(*) FROM reports WHERE status = 'pending_review'").fetchone()[0],
            "donations": db.execute("SELECT COUNT(*) FROM donations WHERE status = 'pending'").fetchone()[0],
            "complaints": db.execute("SELECT COUNT(*) FROM complaints WHERE status = 'open'").fetchone()[0],
            "volunteers": db.execute("SELECT COUNT(*) FROM users WHERE account_type = 'Volunteer'").fetchone()[0],
        }
        reports = db.execute("SELECT * FROM reports WHERE status = 'pending_review' ORDER BY id DESC LIMIT 20").fetchall()
        donations = db.execute("SELECT * FROM donations WHERE status = 'pending' ORDER BY id DESC LIMIT 20").fetchall()
        complaints = db.execute("SELECT * FROM complaints WHERE status = 'open' ORDER BY id DESC LIMIT 20").fetchall()
    return render_template("admin_dashboard.html", counts=counts, reports=reports, donations=donations, complaints=complaints)


@web.get("/volunteer/profile")
def volunteer_profile():
    """Show a volunteer's account details and saved activity registrations."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("web.login_page"))
    if session.get("account_type") != "Volunteer":
        abort(403)
    with database() as db:
        volunteer = db.execute(
            "SELECT full_name, email, phone, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        signups = db.execute(
            "SELECT activity, contact, note, created_at FROM volunteer_signups "
            "WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    return render_template("volunteer_profile.html", volunteer=volunteer, signups=signups)


@web.post("/api/signup")
def signup():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    account_type = str(data.get("accountType", "Community member")).strip()
    password = str(data.get("password", ""))
    if not name or not phone or not email or len(password) < 8:
        return json_error("Enter your name, phone, email, and a password with at least 8 characters.")
    if account_type not in {"Community member", "Volunteer", "Admin"}:
        account_type = "Community member"
    if account_type == "Admin":
        provided_pass = str(data.get("adminPass", ""))
        expected_pass = str(current_app.config["ADMIN_REGISTRATION_PASS"])
        if not hmac.compare_digest(provided_pass, expected_pass):
            return json_error("The administrator access phrase is incorrect.", 403)
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    try:
        with database() as db:
            db.execute(
                "INSERT INTO users(full_name,phone,email,account_type,password_hash,password_salt,created_at) VALUES(?,?,?,?,?,?,?)",
                (name, phone, email, account_type, password_hash.hex(), salt.hex(), now_iso()),
            )
            user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    except sqlite3.IntegrityError:
        return json_error("That email or phone number is already registered.", 409)
    session.clear()
    session["user_id"] = user_id
    session["user_name"] = name
    session["account_type"] = account_type
    return jsonify({"message": "Your account was created.", "name": name, "accountType": account_type}), 201


@web.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    identity = str(data.get("identity", "")).strip()
    password = str(data.get("password", ""))
    with database() as db:
        user = db.execute(
            "SELECT * FROM users WHERE email = ? COLLATE NOCASE OR phone = ?", (identity, identity)
        ).fetchone()
    if not user:
        return json_error("Email, phone number, or password is incorrect.", 401)
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(user["password_salt"]), 310_000
    ).hex()
    if not hmac.compare_digest(candidate, user["password_hash"]):
        return json_error("Email, phone number, or password is incorrect.", 401)
    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["full_name"]
    session["account_type"] = user["account_type"]
    return jsonify({"message": "You are signed in.", "name": user["full_name"], "accountType": user["account_type"]})


@web.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"message": "You are signed out."})


@web.get("/api/session")
def current_session():
    """Return the small amount of session data needed by the site header."""
    if not session.get("user_id"):
        return jsonify({"authenticated": False})
    return jsonify(
        {
            "authenticated": True,
            "name": session.get("user_name", "Member"),
            "accountType": session.get("account_type", "Community member"),
        }
    )


@web.get("/api/reports")
def list_reports():
    with database() as db:
        rows = db.execute(
            "SELECT id,kind,title,category,report_date AS date,location,description AS text "
            "FROM reports WHERE status='published' ORDER BY id DESC LIMIT 100"
        ).fetchall()
    return jsonify([dict(row) for row in rows])


@web.post("/api/reports")
def create_report():
    data = request.get_json(silent=True) or {}
    kind = str(data.get("kind", "")).strip().lower()
    title = str(data.get("title", "")).strip()
    category = str(data.get("category", "")).strip()
    location = str(data.get("location", "")).strip()
    description = str(data.get("description", "")).strip()
    report_date = str(data.get("date", "")).strip()
    if kind not in {"lost", "found", "missing"}:
        return json_error("Choose lost, found, or missing person report type.")
    if not all((title, category, location, description, report_date)):
        return json_error("Complete all required report fields.")
    try:
        date.fromisoformat(report_date)
    except ValueError:
        return json_error("Enter a valid report date.")
    status = "pending_review" if kind == "missing" else "published"
    with database() as db:
        cur = db.execute(
            "INSERT INTO reports(kind,title,category,report_date,location,description,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (kind, title, category, report_date, location, description, status, now_iso()),
        )
        report_id = cur.lastrowid
    return jsonify({"id": report_id, "status": status, "message": "Saved to the local database."}), 201


@web.post("/api/donations")
def create_donation():
    data = request.get_json(silent=True) or {}
    donor_name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    method = str(data.get("method", "")).strip()
    note = str(data.get("note", "")).strip()
    try:
        amount = float(data.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0
    if not donor_name or not email or not method or amount <= 0:
        return json_error("Enter your name, email, donation amount, and payment method.")
    with database() as db:
        cur = db.execute(
            "INSERT INTO donations(donor_name,email,amount,method,note,created_at) VALUES(?,?,?,?,?,?)",
            (donor_name, email, amount, method, note, now_iso()),
        )
    return jsonify({"id": cur.lastrowid, "message": "Your donation has been submitted for review."}), 201


@web.post("/api/complaints")
def create_complaint():
    data = request.get_json(silent=True) or {}
    full_name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    subject = str(data.get("subject", "")).strip()
    message = str(data.get("message", "")).strip()
    if not all((full_name, email, subject, message)):
        return json_error("Enter your name, email, subject, and complaint details.")
    with database() as db:
        cur = db.execute(
            "INSERT INTO complaints(full_name,email,subject,message,created_at) VALUES(?,?,?,?,?)",
            (full_name, email, subject, message, now_iso()),
        )
    return jsonify({"id": cur.lastrowid, "message": "Your complaint has been sent for review."}), 201


@web.post("/api/admin/reports/<int:report_id>")
def review_report(report_id):
    guard = admin_api_guard()
    if guard:
        return guard
    status = str((request.get_json(silent=True) or {}).get("status", ""))
    if status not in {"published", "rejected"}:
        return json_error("Choose publish or reject.")
    with database() as db:
        cur = db.execute("UPDATE reports SET status = ? WHERE id = ?", (status, report_id))
    if not cur.rowcount:
        return json_error("Report not found.", 404)
    return jsonify({"message": "Report review saved."})


@web.post("/api/admin/donations/<int:donation_id>")
def review_donation(donation_id):
    guard = admin_api_guard()
    if guard:
        return guard
    status = str((request.get_json(silent=True) or {}).get("status", ""))
    if status not in {"accepted", "rejected"}:
        return json_error("Choose accept or reject.")
    with database() as db:
        cur = db.execute(
            "UPDATE donations SET status = ?, reviewed_at = ?, reviewed_by = ? WHERE id = ?",
            (status, now_iso(), session["user_id"], donation_id),
        )
    if not cur.rowcount:
        return json_error("Donation not found.", 404)
    return jsonify({"message": "Donation review saved."})


@web.post("/api/admin/complaints/<int:complaint_id>")
def review_complaint(complaint_id):
    guard = admin_api_guard()
    if guard:
        return guard
    status = str((request.get_json(silent=True) or {}).get("status", ""))
    if status not in {"resolved", "rejected"}:
        return json_error("Choose resolve or reject.")
    with database() as db:
        cur = db.execute(
            "UPDATE complaints SET status = ?, reviewed_at = ?, reviewed_by = ? WHERE id = ?",
            (status, now_iso(), session["user_id"], complaint_id),
        )
    if not cur.rowcount:
        return json_error("Complaint not found.", 404)
    return jsonify({"message": "Complaint review saved."})


@web.post("/api/volunteer-signups")
def volunteer_signup():
    user_id = session.get("user_id")
    if not user_id or session.get("account_type") != "Volunteer":
        return json_error("Please sign in with a Volunteer account to join an activity.", 403)
    data = request.get_json(silent=True) or {}
    activity = str(data.get("activity", "")).strip()
    full_name = str(data.get("name", "")).strip()
    contact = str(data.get("contact", "")).strip()
    note = str(data.get("note", "")).strip()
    if not all((activity, full_name, contact)):
        return json_error("Activity, name, and contact are required.")
    with database() as db:
        cur = db.execute(
            "INSERT INTO volunteer_signups(user_id,activity,full_name,contact,note,created_at) VALUES(?,?,?,?,?,?)",
            (user_id, activity, full_name, contact, note, now_iso()),
        )
    return jsonify({"id": cur.lastrowid, "message": "Your interest was saved locally."}), 201
