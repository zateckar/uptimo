from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app.forms.auth import LoginForm

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash(
                    "Your account has been deactivated. Please contact support.",
                    "danger",
                )
                return render_template("auth/login.html", form=form)

            login_user(user, remember=form.remember_me.data)
            user.update_last_login()

            next_page = request.args.get("next")
            if not next_page or url_for("dashboard.index") not in next_page:
                next_page = url_for("dashboard.index")

            flash("Welcome back!", "success")
            return redirect(next_page)
        else:
            flash("Invalid username or password", "danger")

    return render_template("auth/login.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/profile")
@login_required
def profile():
    """Show user profile"""
    return render_template("auth/profile.html")
