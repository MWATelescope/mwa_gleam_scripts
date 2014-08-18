"""add admin_level to users

Revision ID: 32e648ccb976
Revises: 1067c96c7619
Create Date: 2014-08-05 06:13:54.022901

"""

# revision identifiers, used by Alembic.
revision = '32e648ccb976'
down_revision = '1067c96c7619'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Integer


def upgrade():
  op.add_column('user',
    sa.Column('admin_level', Integer)
  )


def downgrade():
  op.drop_column('user', 'admin_level')
