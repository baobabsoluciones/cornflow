"""
Modification to users table

Revision ID: 4aac5e0c6e66
Revises: c8a6c762e818
Create Date: 2021-06-14 13:58:02.306535

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "4aac5e0c6e66"
down_revision = "c8a6c762e818"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    # First change - add "first_name" column
    op.add_column(
        "users", sa.Column("first_name", sa.String(length=128), nullable=True)
    )

    # Second change - drop column "admin"
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("admin")

    # Third change - drop column "super_admin"
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("super_admin")

    # Fourth change - drop column "name"
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("name")

    # Fifth change - username not null
    op.execute("UPDATE users SET username = id")
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("username", nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    # First change - drop column first_name
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("first_name")

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_table("username", nullable=True)

    # Second change - add column "admin", nullable and False by default
    op.add_column(
        "users",
        sa.Column(
            "admin", sa.BOOLEAN(), server_default=sa.text("(false)"), nullable=True
        ),
    )

    # Third change - add column "super_admin", nullable and False by default
    op.add_column(
        "users",
        sa.Column(
            "super_admin",
            sa.BOOLEAN(),
            server_default=sa.text("(false)"),
            nullable=True,
        ),
    )

    # Fourth change - add column "name", nullable
    op.add_column("users", sa.Column("name", sa.VARCHAR(length=128), nullable=True))

    # ### end Alembic commands ###
