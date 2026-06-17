"""empty message

Revision ID: 4729cd156460
Revises: 9cacf194fa1c
Create Date: 2026-05-07 14:58:53.461691

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4729cd156460"
down_revision = "9cacf194fa1c"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("executions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("execution_files_status", sa.SmallInteger(), nullable=True)
        )

    op.execute(
        'update "executions" set execution_files_status = 0 where execution_files_status is null'
    )

    with op.batch_alter_table("executions", schema=None) as batch_op:
        batch_op.alter_column(
            "execution_files_status", existing_type=sa.SmallInteger(), nullable=False
        )


def downgrade():
    with op.batch_alter_table("executions", schema=None) as batch_op:
        batch_op.drop_column("execution_files_status")
