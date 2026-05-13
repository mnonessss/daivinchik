"""profile photos s3 object key

Revision ID: e1f2a3b4c5d6
Revises: cd42d8d5e101
Create Date: 2026-05-13 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "cd42d8d5e101"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("profile_photos", sa.Column("s3_object_key", sa.String(), nullable=True))
    op.alter_column(
        "profile_photos",
        "telegram_file_id",
        existing_type=sa.String(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "profile_photos",
        "telegram_file_id",
        existing_type=sa.String(),
        nullable=False,
    )
    op.drop_column("profile_photos", "s3_object_key")
