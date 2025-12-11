"""Public status page routes - no authentication required."""

from typing import Any

from flask import Blueprint, abort, current_app, render_template

from app import limiter
from app.models.public_status_page import PublicStatusPage
from app.services.public_status_service import PublicStatusService

bp = Blueprint("public_status", __name__)


@bp.route("/status")
def public_status_simple() -> Any:
    """Public status page with simple URL."""
    # Apply rate limiting if limiter is available
    if limiter:
        return limiter.limit("30 per minute")(_public_status_simple_impl)()
    return _public_status_simple_impl()


def _public_status_simple_impl() -> Any:
    """Implementation for simple status page."""
    status_page = PublicStatusService.get_active_simple_status_page()

    if not status_page:
        abort(404)

    # Type assertion: we know status_page is not None here
    return _render_public_status_page(status_page)  # type: ignore[arg-type]


@bp.route("/status/<string:page_uuid>")
def public_status_uuid(page_uuid: str) -> Any:
    """Public status page with UUID URL."""
    # Apply rate limiting if limiter is available
    if limiter:
        return limiter.limit("30 per minute")(_public_status_uuid_impl)(page_uuid)
    return _public_status_uuid_impl(page_uuid)


def _public_status_uuid_impl(page_uuid: str) -> Any:
    """Implementation for UUID status page."""
    status_page = PublicStatusService.get_active_status_page_by_uuid(page_uuid)

    if not status_page:
        abort(404)

    # Type assertion: we know status_page is not None here
    return _render_public_status_page(status_page)  # type: ignore[arg-type]


def _render_public_status_page(status_page: PublicStatusPage) -> str:  # type: ignore[assignment]
    """Render public status page using the service layer."""
    try:
        # Get fresh data for rendering (caching removed)
        status_data = PublicStatusService.get_cached_public_status_data(status_page)

        return render_template(
            "public/status.html",
            status_page=status_data["status_page"],
            overall_status=status_data["overall_status"],
            monitors=status_data["monitors"],
            heartbeats=status_data["heartbeats"],
            last_updated=status_data["last_updated"],
        )

    except Exception as e:
        current_app.logger.error(f"Error rendering public status page: {e}")
        abort(500)
