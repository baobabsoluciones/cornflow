"""API key metadata: issue timestamp, scope, expiry notice and rotation grace

Revision ID: d4e8b2c6f109
Revises: c3f2a1b4e5d6
Create Date: 2026-07-27

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d4e8b2c6f109"
down_revision = "c3f2a1b4e5d6"
branch_labels = None
depends_on = None


def upgrade():
    # The API key itself is never stored: only the metadata needed to compute
    # and notify its expiry, remember its scope and honour the rotation grace.
    op.add_column("users", sa.Column("api_key_issued_at", sa.DateTime(), nullable=True))
    op.add_column(
        "users", sa.Column("api_key_scope", sa.String(length=16), nullable=True)
    )
    op.add_column(
        "users", sa.Column("api_key_expiry_notified", sa.Integer(), nullable=True)
    )
    op.add_column(
        "users", sa.Column("api_key_previous_version", sa.Integer(), nullable=True)
    )
    op.add_column(
        "users", sa.Column("api_key_grace_until", sa.DateTime(), nullable=True)
    )


def downgrade():
    op.drop_column("users", "api_key_grace_until")
    op.drop_column("users", "api_key_previous_version")
    op.drop_column("users", "api_key_expiry_notified")
    op.drop_column("users", "api_key_scope")
    op.drop_column("users", "api_key_issued_at")
