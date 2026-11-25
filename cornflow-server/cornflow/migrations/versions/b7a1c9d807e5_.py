"""Security hardening: MFA columns, forced password change flag,
password history and MFA backup codes tables

Revision ID: b7a1c9d807e5
Revises: 4729cd156460
Create Date: 2026-07-25

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7a1c9d807e5"
down_revision = "4729cd156460"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column(
            "pwd_change_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "users", sa.Column("totp_secret", sa.String(length=256), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "locked", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "token_version", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "users", sa.Column("totp_last_counter", sa.Integer(), nullable=True)
    )
    op.add_column(
        "users", sa.Column("last_login_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "api_key_version", sa.Integer(), nullable=False, server_default="0"
        ),
    )

    op.create_table(
        "user_password_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("password_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_password_history_user_id"),
        "user_password_history",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "mfa_backup_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_mfa_backup_codes_user_id"),
        "mfa_backup_codes",
        ["user_id"],
        unique=False,
    )

    # Existing internal users (the ones with a stored password) must set a
    # policy-compliant password at their next login
    users = sa.table(
        "users",
        sa.column("password", sa.String),
        sa.column("pwd_change_required", sa.Boolean),
    )
    op.execute(
        users.update()
        .where(users.c.password.isnot(None))
        .values(pwd_change_required=True)
    )


def downgrade():
    op.drop_index(
        op.f("ix_mfa_backup_codes_user_id"), table_name="mfa_backup_codes"
    )
    op.drop_table("mfa_backup_codes")
    op.drop_index(
        op.f("ix_user_password_history_user_id"), table_name="user_password_history"
    )
    op.drop_table("user_password_history")
    op.drop_column("users", "api_key_version")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "totp_last_counter")
    op.drop_column("users", "token_version")
    op.drop_column("users", "locked")
    op.drop_column("users", "failed_login_attempts")
    op.drop_column("users", "mfa_enabled")
    op.drop_column("users", "totp_secret")
    op.drop_column("users", "pwd_change_required")
