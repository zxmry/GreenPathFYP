"""Authentication blueprint: login, signup, logout."""

from flask import (
    Blueprint, render_template, request, redirect, url_for, session, flash,
)
import json
import os

from config import USERS_FILE

auth_bp = Blueprint("auth", __name__)


def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


USERS = load_users()


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
        action = request.form.get("action")
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        if action == "signup":
            name = request.form.get("name", "").strip()
            vehicle = request.form.get("vehicle", "")
            if len(name) < 2 or not vehicle or len(password) < 8:
                flash(
                    "Please fill all fields correctly. Password min 8 chars.",
                    "error",
                )
                return render_template("login.html")
            USERS[phone] = {"name": name, "password": password, "vehicle": vehicle}
            save_users(USERS)
            session["user"] = USERS[phone]
            flash(f"Welcome {name}! Account created.", "success")
            return redirect(url_for("auth.dashboard"))

        elif action == "login":
            user = USERS.get(phone)
            if user and user["password"] == password:
                session["user"] = {
                    "name": user["name"],
                    "phone": phone,
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

