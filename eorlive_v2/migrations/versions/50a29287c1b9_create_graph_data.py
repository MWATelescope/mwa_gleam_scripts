"""create graph_data

Revision ID: 50a29287c1b9
Revises: c62b0aecf16
Create Date: 2014-07-25 02:53:45.542996

"""

# revision identifiers, used by Alembic.
revision = '50a29287c1b9'
down_revision = 'c62b0aecf16'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, TIMESTAMP, func


def upgrade():
    op.create_table(
      'graph_data',
      sa.Column('id', sa.Integer, primary_key=True),
      sa.Column('created_date', TIMESTAMP, server_default=func.now()),
      sa.Column('hours_scheduled', sa.Float),
      sa.Column('hours_observed', sa.Float),
      sa.Column('hours_with_data', sa.Float),
      sa.Column('hours_with_uvfits', sa.Float),
      sa.Column('data_transfer_rate', sa.Float),
    )


def downgrade():
    op.drop_table('graph_data')
