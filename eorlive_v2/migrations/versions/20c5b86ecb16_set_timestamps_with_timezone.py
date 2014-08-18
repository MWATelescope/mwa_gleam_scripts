"""set timestamps with timezone

Revision ID: 20c5b86ecb16
Revises: 50a29287c1b9
Create Date: 2014-07-26 20:38:24.292648

"""

# revision identifiers, used by Alembic.
revision = '20c5b86ecb16'
down_revision = '50a29287c1b9'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column(
        table_name = 'user',
        column_name = 'created_at',
        nullable = False,
        type_ = sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name = 'admin_user',
        column_name = 'created_at',
        nullable = False,
        type_ = sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name = 'graph_data',
        column_name = 'created_date',
        nullable = False,
        type_ = sa.types.DateTime(timezone=True),
    )


def downgrade():
    op.alter_column(
        table_name = 'user',
        column_name = 'created_at',
        type_ = sa.types.DateTime(timezone=False),
    )
    op.alter_column(
        table_name = 'admin_user',
        column_name = 'created_at',
        type_ = sa.types.DateTime(timezone=False),
    )
    op.alter_column(
        table_name = 'graph_data',
        column_name = 'created_date',
        type_ = sa.types.DateTime(timezone=False),
    )
