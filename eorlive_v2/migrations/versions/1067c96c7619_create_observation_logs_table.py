"""create observation_logs table

Revision ID: 1067c96c7619
Revises: 20c5b86ecb16
Create Date: 2014-07-27 18:14:51.957351

"""

# revision identifiers, used by Alembic.
revision = '1067c96c7619'
down_revision = '20c5b86ecb16'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, TIMESTAMP, func


def upgrade():
  op.create_table(
    'observation_log',
    Column('id', sa.Integer, primary_key=True),
    Column('created_date', sa.types.DateTime(timezone=True), server_default=func.now()),
    Column('observed_date', sa.types.DateTime(timezone=True)),
    Column('author_user_id', sa.Integer, sa.ForeignKey('user.id')),
    Column('note', sa.Text),
    Column('tags', sa.Integer, nullable=False, default=0)
  )

def downgrade():
  op.drop_table('observation_log')
