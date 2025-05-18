"""add policy table

Revision ID: 20240609_add_policy_table
Revises: 8a96b0d1a466
Create Date: 2024-06-09

"""

# revision identifiers, used by Alembic.
revision = '20240609_add_policy_table'
down_revision = '8a96b0d1a466'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    """Create policies table"""
    op.create_table(
        'policies',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('assignment_late_penalty', sa.Float, default=10),
        sa.Column('minimum_passing_grade', sa.Float, default=60),
        sa.Column('attendance_requirement', sa.Float, default=75),
        sa.Column('grade_scale', sa.String(20), default='letter'),
        sa.Column('allow_resubmissions', sa.Boolean, default=True),
        sa.Column('max_resubmissions', sa.Integer, default=1),
        sa.Column('notification_lead_time', sa.Integer, default=7)
    )

def downgrade():
    """Drop policies table"""
    op.drop_table('policies')
