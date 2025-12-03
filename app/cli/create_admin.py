"""CLI command for creating admin users."""

import click
from flask.cli import with_appcontext


@click.command()
@click.option("--username", prompt=True, help="Admin username")
@click.option("--email", prompt=True, help="Admin email")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="Admin password",
)
@with_appcontext
def create_admin(username: str, email: str, password: str) -> None:
    """Create an admin user."""
    from app.models.user import User
    from app import db

    # Check if user already exists
    existing_user = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()

    if existing_user:
        if existing_user.username == username:
            click.echo(f"Error: User '{username}' already exists.")
        else:
            click.echo(f"Error: Email '{email}' is already registered.")
        return

    # Create admin user
    admin_user = User(
        username=username,
        email=email,
        is_admin=True,
        is_active=True,
    )
    admin_user.set_password(password)
    db.session.add(admin_user)
    db.session.commit()

    click.echo(f"✅ Admin user '{username}' created successfully!")
    click.echo(f"   Email: {email}")
    click.echo("   You can now log in with these credentials.")


def register_cli_commands(app) -> None:
    """Register CLI commands with the Flask app."""
    app.cli.add_command(create_admin)
