"""
Add kpis column to cases and executions tables

Revision ID: 509d280698e4
Revises: cef1df240b27
Create Date: 2026-03-04 16:16:39.394707

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "509d280698e4"
down_revision = "cef1df240b27"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("cases", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("kpis", postgresql.JSON(astext_type=sa.Text()), nullable=True)
        )

    with op.batch_alter_table("executions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("kpis", postgresql.JSON(astext_type=sa.Text()), nullable=True)
        )

    with op.batch_alter_table("executions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("last_run_checks_and_kpis", sa.Boolean(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("executions", schema=None) as batch_op:
        batch_op.drop_column("last_run_checks_and_kpis")

    with op.batch_alter_table("executions", schema=None) as batch_op:
        batch_op.drop_column("kpis")

    with op.batch_alter_table("cases", schema=None) as batch_op:
        batch_op.drop_column("kpis")
