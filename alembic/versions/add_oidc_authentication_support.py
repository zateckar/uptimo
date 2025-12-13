"""Add OIDC authentication support

Revision ID: add_oidc_authentication_support
Revises: fc8f47027f1b
Create Date: 2024-12-12 21:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "add_oidc_authentication_support"
down_revision: Union[str, None] = "fc8f47027f1b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create oidc_provider table
    op.create_table(
        "oidc_provider",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("issuer_url", sa.String(length=500), nullable=True),
        sa.Column("authorization_endpoint", sa.String(length=500), nullable=True),
        sa.Column("token_endpoint", sa.String(length=500), nullable=True),
        sa.Column("userinfo_endpoint", sa.String(length=500), nullable=True),
        sa.Column("jwks_uri", sa.String(length=500), nullable=True),
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("client_secret", sa.String(length=255), nullable=True),
        sa.Column(
            "scope",
            sa.String(length=100),
            nullable=False,
            default="openid profile email",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_oidc_provider_name"), "oidc_provider", ["name"], unique=True
    )
    op.create_index(op.f("ix_oidc_provider_is_active"), "oidc_provider", ["is_active"])

    # For SQLite, we need to use batch mode to alter the user table
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "auth_type",
                sa.String(length=20),
                nullable=False,
                server_default="local",
            )
        )
        batch_op.add_column(
            sa.Column("oidc_provider", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(
            sa.Column("oidc_subject", sa.String(length=255), nullable=True)
        )
        batch_op.create_index("ix_user_auth_type", ["auth_type"])
        batch_op.create_index("ix_user_oidc_provider", ["oidc_provider"])
        batch_op.create_index("ix_user_oidc_subject", ["oidc_subject"])
        batch_op.create_index(
            "idx_oidc_identity", ["oidc_provider", "oidc_subject"], unique=False
        )


def downgrade() -> None:
    # Drop indexes first
    op.drop_index("idx_oidc_identity", table_name="user")
    op.drop_index("ix_user_oidc_subject", table_name="user")
    op.drop_index("ix_user_oidc_provider", table_name="user")
    op.drop_index("ix_user_auth_type", table_name="user")

    # Remove columns from user table using batch mode for SQLite
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("oidc_subject")
        batch_op.drop_column("oidc_provider")
        batch_op.drop_column("auth_type")

    # Drop oidc_provider table
    op.drop_index(op.f("ix_oidc_provider_is_active"), table_name="oidc_provider")
    op.drop_index(op.f("ix_oidc_provider_name"), table_name="oidc_provider")
    op.drop_table("oidc_provider")
