"""add deleted_date to observation log

Revision ID: 51dd9adb085e
Revises: 178a0ad66de9
Create Date: 2014-08-17 22:38:39.019726

"""

# revision identifiers, used by Alembic.
revision = '51dd9adb085e'
down_revision = '178a0ad66de9'

from alembic import op
import sqlalchemy as sa


def upgrade():
  op.add_column('observation_log',
    sa.Column('deleted_date', sa.types.DateTime(timezone=True))
  )


def downgrade():
  op.drop_column('user', 'deleted_date')
