from urllib.parse import urljoin, urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_

from food_ordering import db
from food_ordering.models import User

auth_bp = Blueprint("auth", __name__)


def _is_safe_redirect_url(target):
    if not target:
        return False
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in ("http", "https") and host_url.netloc == redirect_url.netloc


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if User.query.filter_by(username=username).first():
            flash("This username is already taken.", "warning")
            return render_template("register.html")

        if User.query.filter_by(email=email).first():
            flash("This email is already registered.", "warning")
            return render_template("register.html")

        user = User(name=name, username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next")

    if current_user.is_authenticated:
        if _is_safe_redirect_url(next_url):
            return redirect(next_url)
        return redirect(url_for("main.index"))

    if request.method == "POST":
        login_value = request.form.get("login", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter(
            or_(
                User.email == login_value,
                User.username == login_value,
            )
        ).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Welcome back.", "success")
            if _is_safe_redirect_url(next_url):
                return redirect(next_url)
            return redirect(url_for("main.index"))

        flash("Invalid email, username, or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
