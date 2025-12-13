import time
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    session,
    current_app,
)
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app.models.oidc_provider import OIDCProvider
from app.forms.auth import LoginForm
from app.services.oidc_service import OIDCService

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()

    # Get active OIDC providers for template
    oidc_providers = OIDCProvider.query.filter_by(is_active=True).all()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash(
                    "Your account has been deactivated. Please contact support.",
                    "danger",
                )
                return render_template(
                    "auth/login.html", form=form, oidc_providers=oidc_providers
                )

            login_user(user, remember=form.remember_me.data)
            user.update_last_login()

            next_page = request.args.get("next")
            if not next_page or url_for("dashboard.index") not in next_page:
                next_page = url_for("dashboard.index")

            flash("Welcome back!", "success")
            return redirect(next_page)
        else:
            flash("Invalid username or password", "danger")

    return render_template("auth/login.html", form=form, oidc_providers=oidc_providers)


@bp.route("/login/oidc/<provider_name>")
def login_oidc(provider_name: str):
    """Initiate OIDC login with discovery support"""
    try:
        provider = OIDCProvider.query.filter_by(
            name=provider_name, is_active=True
        ).first()

        if not provider:
            flash("Invalid authentication provider", "danger")
            return redirect(url_for("auth.login"))

        # Generate PKCE, state, and nonce
        code_verifier, code_challenge, state, nonce = OIDCService.generate_pkce()

        # Store in session with expiration
        session[f"oidc_{provider_name}_data"] = {
            "code_verifier": code_verifier,
            "state": state,
            "nonce": nonce,
            "created_at": time.time(),
        }

        # Get provider endpoints (with discovery)
        provider_data = provider.get_endpoint_data()

        # Build auth URL
        redirect_uri = url_for(
            "auth.oidc_callback", provider_name=provider_name, _external=True
        )
        auth_url = OIDCService.build_auth_url(
            provider_data, redirect_uri, code_challenge, state, nonce
        )

        return redirect(auth_url)

    except Exception as e:
        current_app.logger.error(f"OIDC login error for {provider_name}: {e}")
        flash("Authentication setup failed", "danger")
        return redirect(url_for("auth.login"))


@bp.route("/auth/oidc/<provider_name>/callback")
def oidc_callback(provider_name: str):
    """Handle OIDC callback with enhanced validation"""
    try:
        # Get stored session data
        oidc_data = session.get(f"oidc_{provider_name}_data")
        if not oidc_data:
            flash("Authentication session expired", "danger")
            return redirect(url_for("auth.login"))

        # Check session age (10 minutes)
        if time.time() - oidc_data["created_at"] > 600:
            session.pop(f"oidc_{provider_name}_data", None)
            flash("Authentication session expired", "danger")
            return redirect(url_for("auth.login"))

        # Verify state
        if oidc_data["state"] != request.args.get("state"):
            flash("Invalid state parameter", "danger")
            return redirect(url_for("auth.login"))

        # Get authorization code
        code = request.args.get("code")
        if not code:
            flash("Authorization code not received", "danger")
            return redirect(url_for("auth.login"))

        # Get provider and endpoints
        provider = OIDCProvider.query.filter_by(
            name=provider_name, is_active=True
        ).first()

        if not provider:
            flash("Invalid authentication provider", "danger")
            return redirect(url_for("auth.login"))

        provider_data = provider.get_endpoint_data()

        # Exchange code for tokens
        redirect_uri = url_for(
            "auth.oidc_callback", provider_name=provider_name, _external=True
        )
        tokens = OIDCService.exchange_code_for_tokens(
            provider_data, code, redirect_uri, oidc_data["code_verifier"]
        )

        # Validate ID token
        id_token = tokens.get("id_token")
        if not id_token:
            flash("ID token not received", "danger")
            return redirect(url_for("auth.login"))

        claims = OIDCService.validate_id_token(
            id_token, provider_data, oidc_data["nonce"]
        )

        # Find or create user
        user = OIDCService.find_or_create_user(claims, provider_name)

        if not user.is_active:
            flash("Your account has been deactivated", "danger")
            return redirect(url_for("auth.login"))

        # Login user
        login_user(user, remember=True)
        user.update_last_login()

        # Clean up session
        session.pop(f"oidc_{provider_name}_data", None)

        flash(f"Successfully logged in with {provider.display_name}!", "success")
        return redirect(url_for("dashboard.index"))

    except Exception as e:
        current_app.logger.error(f"OIDC callback error for {provider_name}: {e}")
        flash("Authentication failed", "danger")
        return redirect(url_for("auth.login"))


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
