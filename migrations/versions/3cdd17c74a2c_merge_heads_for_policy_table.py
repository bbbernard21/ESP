"""merge heads for policy table

Revision ID: 3cdd17c74a2c
Revises: 20240609_add_policy_table, 7bf6dda76e8c
Create Date: 2025-05-05 18:26:54.403201

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3cdd17c74a2c'
down_revision = ('20240609_add_policy_table', '7bf6dda76e8c')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
