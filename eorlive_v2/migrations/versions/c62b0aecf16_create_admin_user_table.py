"""create admin_user table

Revision ID: c62b0aecf16
Revises: d6de23102a1
Create Date: 2014-07-06 23:35:23.688446

"""

# revision identifiers, used by Alembic.
revision = 'c62b0aecf16'
down_revision = 'd6de23102a1'

from alembic import op
import sqlalchemy as sa


def upgrade():
  op.create_table(
    'admin_user',
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.String(128)),
    sa.Column('username', sa.String(128)),
    sa.Column('email', sa.String(128), unique=True),
    sa.Column('password', sa.String(64)),
    sa.Column('created_at', sa.DateTime)
  )


def downgrade():
  op.drop_table('admin_user')
