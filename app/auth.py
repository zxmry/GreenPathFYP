"""Authentication blueprint — SQLite version.

Replaces users.json read/write with direct SQL queries.
All routes, flash messages and session behaviour are identical
to the original so the frontend needs no changes at all.
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for, session, flash,
)
from datetime import datetime
from app.database import get_connection

auth_bp = Blueprint("auth", __name__)


def login_required(f):
    def wrap(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap


@auth_bp.route("/")
def home():
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        action   = request.form.get("action")
        phone    = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        if action == "signup":
            name    = request.form.get("name", "").strip()
            vehicle = request.form.get("vehicle", "")

            if len(name) < 2 or not vehicle or len(password) < 8:
                flash("Please fill all fields correctly. Password min 8 chars.", "error")
                return render_template("login.html")

            conn = get_connection()
            # Check if phone already registered
            existing = conn.execute(
                "SELECT phone FROM users WHERE phone = ?", (phone,)
            ).fetchone()

            if existing:
                conn.close()
                flash("Phone number already registered. Please log in.", "error")
                return render_template("login.html")

            with conn:
                conn.execute("""
                    INSERT INTO users (phone, name, password, vehicle, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (phone, name, password, vehicle,
                      datetime.now().strftime("%Y-%m-%dT%H:%M:%S")))
            conn.close()

            session["user"] = {"name": name, "phone": phone, "vehicle": vehicle}
            flash(f"Welcome {name}! Account created.", "success")
            return redirect(url_for("auth.dashboard"))

        elif action == "login":
            conn = get_connection()
            user = conn.execute(
                "SELECT * FROM users WHERE phone = ?", (phone,)
            ).fetchone()
            conn.close()

            if user and user["password"] == password:
                session["user"] = {
                    "name":    user["name"],
                    "phone":   user["phone"],
                    "vehicle": user["vehicle"],
                }
                flash(f'Welcome back, {user["name"]}!', "success")
                return redirect(url_for("auth.dashboard"))
            else:
                flash("Invalid phone or password.", "error")

    return render_template("login.html")


@auth_bp.route("/dashboard")
def dashboard():
    if "user" not in session:
        flash("Please log in to access dashboard.", "warning")
        return redirect(url_for("auth.login"))
    return render_template("index.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login"))
