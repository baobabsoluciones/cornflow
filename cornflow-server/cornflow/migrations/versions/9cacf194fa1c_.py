"""
Add kpis_schema to deployed_workflows, add checks_and_kpis_only to execution

Revision ID: 9cacf194fa1c
Revises: 509d280698e4
Create Date: 2026-04-13 09:44:59.661880

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "9cacf194fa1c"
down_revision = "509d280698e4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("deployed_workflows", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "kpis_schema", postgresql.JSON(astext_type=sa.Text()), nullable=True
            )
        )

    with op.batch_alter_table("executions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("checks_and_kpis_only", sa.Boolean(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("executions", schema=None) as batch_op:
        batch_op.drop_column("checks_and_kpis_only")

    with op.batch_alter_table("deployed_workflows", schema=None) as batch_op:
        batch_op.drop_column("kpis_schema")
