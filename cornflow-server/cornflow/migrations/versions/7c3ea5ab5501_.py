"""Add schemas to DeployedDag table

Revision ID: 7c3ea5ab5501
Revises: d0e0700dcd8e
Create Date: 2023-02-03 13:51:28.101001

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "7c3ea5ab5501"
down_revision = "d0e0700dcd8e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "deployed_dags",
        sa.Column(
            "instance_schema", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "deployed_dags",
        sa.Column(
            "solution_schema", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "deployed_dags",
        sa.Column(
            "config_schema", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "deployed_dags",
        sa.Column(
            "instance_checks_schema",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "deployed_dags",
        sa.Column(
            "solution_checks_schema",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("deployed_dags", "instance_schema")
    op.drop_column("deployed_dags", "solution_schema")
    op.drop_column("deployed_dags", "config_schema")
    op.drop_column("deployed_dags", "instance_checks_schema")
    op.drop_column("deployed_dags", "solution_checks_schema")
