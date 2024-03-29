"""
Renamed column in executions model. Added hash to data an solution

Revision ID: 1af47a419bbd
Revises: e937a5234ce4
Create Date: 2021-04-13 12:44:26.132489

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "1af47a419bbd"
down_revision = "e937a5234ce4"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "executions",
        sa.Column("data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "executions", sa.Column("data_hash", sa.String(length=256), nullable=True)
    )
    op.execute("UPDATE executions SET data_hash = ''")

    with op.batch_alter_table("executions") as batch_op:
        batch_op.alter_column("data_hash", nullable=False)

    # workaround to make migration work in sqlite:
    with op.batch_alter_table("executions") as batch_op:
        batch_op.drop_column("execution_results")

    op.add_column(
        "instances", sa.Column("data_hash", sa.String(length=256), nullable=True)
    )
    op.execute("UPDATE instances SET data_hash = ''")
    with op.batch_alter_table("instances") as batch_op:
        batch_op.alter_column("data_hash", nullable=False)

    with op.batch_alter_table("instances") as batch_op:
        batch_op.alter_column("data", existing_type=postgresql.JSON(), nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "instances", "data", existing_type=postgresql.JSON(), nullable=False
    )
    op.drop_column("instances", "data_hash")
    op.add_column(
        "executions", sa.Column("execution_results", postgresql.JSON(), nullable=True)
    )
    op.drop_column("executions", "data_hash")
    # ### end Alembic commands ###
