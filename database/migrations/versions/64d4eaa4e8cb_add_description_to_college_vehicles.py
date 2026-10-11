"""add_description_to_college_vehicles

Revision ID: 64d4eaa4e8cb
Revises: 17cb7593c420
Create Date: 2026-10-11 11:24:02.918543

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '64d4eaa4e8cb'
down_revision: Union[str, Sequence[str], None] = '17cb7593c420'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('college_vehicles', sa.Column('description', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('college_vehicles', 'description')
