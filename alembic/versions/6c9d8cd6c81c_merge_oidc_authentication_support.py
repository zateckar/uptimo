"""merge oidc authentication support

Revision ID: 6c9d8cd6c81c
Revises: 579ac7ed1c53, add_oidc_authentication_support
Create Date: 2025-12-13 21:46:19.620007

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "6c9d8cd6c81c"
down_revision: Union[str, None] = ("579ac7ed1c53", "add_oidc_authentication_support")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
