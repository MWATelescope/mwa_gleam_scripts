"""create user table

Revision ID: d6de23102a1
Revises: None
Create Date: 2014-07-06 23:35:16.823567

"""

# revision identifiers, used by Alembic.
revision = 'd6de23102a1'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
  op.create_table(
    'user',
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.String(128)),
    sa.Column('username', sa.String(128)),
    sa.Column('email', sa.String(128), unique=True),
    sa.Column('password', sa.String(64)),
    sa.Column('created_at', sa.DateTime)
  )

def downgrade():
  op.drop_table('user')
