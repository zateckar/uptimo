"""CLI command to clear TLS certificate cache."""

import click
from flask import Flask
from flask.cli import with_appcontext

from app import db
from app.models.deduplication import TLSCertificate


def register_cli_commands(app: Flask) -> None:
    """Register CLI commands with the Flask application."""
    app.cli.add_command(clear_tls_certs)


@click.command("clear-tls-certs")
@with_appcontext
def clear_tls_certs():
    """Clear all TLS certificate records to force refresh with complete data."""
    try:
        count = TLSCertificate.query.count()
        TLSCertificate.query.delete()
        db.session.commit()
        click.echo(f"Successfully deleted {count} TLS certificate records.")
        click.echo("Certificates will be re-collected on next monitor check.")
    except Exception as e:
        db.session.rollback()
        click.echo(f"Error clearing TLS certificates: {str(e)}", err=True)
