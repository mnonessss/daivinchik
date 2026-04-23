"""add profile_photos table

Revision ID: 9b8f4d2a1c3e
Revises: 715e4b4fd865
Create Date: 2026-04-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9b8f4d2a1c3e"
down_revision: Union[str, Sequence[str], None] = "715e4b4fd865"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "profile_photos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("telegram_file_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_profile_photos_id"), "profile_photos", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_profile_photos_id"), table_name="profile_photos")
    op.drop_table("profile_photos")
