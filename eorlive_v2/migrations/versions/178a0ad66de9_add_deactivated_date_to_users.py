"""add deactivated_date to users

Revision ID: 178a0ad66de9
Revises: 32e648ccb976
Create Date: 2014-08-05 06:32:32.863102

"""

# revision identifiers, used by Alembic.
revision = '178a0ad66de9'
down_revision = '32e648ccb976'

from alembic import op
import sqlalchemy as sa


def upgrade():
  op.add_column('user',
    sa.Column('deactivated_date', sa.types.DateTime(timezone=True))
  )


def downgrade():
  op.drop_column('user', 'deactivated_date')
