"""
Added pwd_last_change column to users table

Revision ID: 991b98e24225
Revises: ebdd955fcc5e
Create Date: 2024-01-31 19:17:18.009264

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "991b98e24225"
down_revision = "ebdd955fcc5e"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("pwd_last_change", sa.DateTime(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("pwd_last_change")

    # ### end Alembic commands ###
