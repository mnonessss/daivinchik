"""add indexes for performance and referrals

Revision ID: cd42d8d5e101
Revises: 9b8f4d2a1c3e
Create Date: 2026-05-12 13:40:00.000000
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "cd42d8d5e101"
down_revision: Union[str, Sequence[str], None] = "9b8f4d2a1c3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_users_referral_id", "users", ["referral_id"], unique=False)
    op.create_index("ix_profiles_age", "profiles", ["age"], unique=False)
    op.create_index("ix_profiles_gender", "profiles", ["gender"], unique=False)
    op.create_index("ix_profiles_city", "profiles", ["city"], unique=False)
    op.create_index("ix_ranking_user_id", "ranking", ["user_id"], unique=True)
    op.create_index("ix_interactions_from_user", "interactions", ["from_user"], unique=False)
    op.create_index("ix_interactions_to_user", "interactions", ["to_user"], unique=False)
    op.create_index("ix_interactions_action", "interactions", ["action"], unique=False)
    op.create_index(
        "ix_interactions_from_to_action",
        "interactions",
        ["from_user", "to_user", "action"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_interactions_from_to_action", table_name="interactions")
    op.drop_index("ix_interactions_action", table_name="interactions")
    op.drop_index("ix_interactions_to_user", table_name="interactions")
    op.drop_index("ix_interactions_from_user", table_name="interactions")
    op.drop_index("ix_ranking_user_id", table_name="ranking")
    op.drop_index("ix_profiles_city", table_name="profiles")
    op.drop_index("ix_profiles_gender", table_name="profiles")
    op.drop_index("ix_profiles_age", table_name="profiles")
    op.drop_index("ix_users_referral_id", table_name="users")
