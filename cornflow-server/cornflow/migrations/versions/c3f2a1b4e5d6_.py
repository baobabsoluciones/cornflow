"""Refresh-token sessions: session_tokens table

Revision ID: c3f2a1b4e5d6
Revises: b7a1c9d807e5
Create Date: 2026-07-26

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c3f2a1b4e5d6"
down_revision = "b7a1c9d807e5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "session_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "revoked", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_session_tokens_session_id"),
        "session_tokens",
        ["session_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_session_tokens_jti"), "session_tokens", ["jti"], unique=False
    )
    op.create_index(
        op.f("ix_session_tokens_user_id"),
        "session_tokens",
        ["user_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_session_tokens_user_id"), table_name="session_tokens")
    op.drop_index(op.f("ix_session_tokens_jti"), table_name="session_tokens")
    op.drop_index(
        op.f("ix_session_tokens_session_id"), table_name="session_tokens"
    )
    op.drop_table("session_tokens")
