"""Add geography tables (province, city, kanwil, kpp)

Revision ID: 004_add_geography
Revises: 003_add_graph_intelligence
Create Date: 2026-03-14
"""
from alembic import op
import sqlalchemy as sa

revision = '004_add_geography'
down_revision = '003_add_graph_intelligence'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'province',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('code', sa.String(10), nullable=True),
    )

    op.create_table(
        'city',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(100), nullable=False, index=True),
        sa.Column('province_id', sa.Integer(), sa.ForeignKey('province.id'), nullable=True, index=True),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lon', sa.Float(), nullable=True),
    )

    op.create_table(
        'kanwil',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(150), nullable=False, unique=True, index=True),
        sa.Column('code', sa.String(20), nullable=True, unique=True),
        sa.Column('province_id', sa.Integer(), sa.ForeignKey('province.id'), nullable=True, index=True),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lon', sa.Float(), nullable=True),
    )

    op.create_table(
        'kpp',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(150), nullable=False, index=True),
        sa.Column('code', sa.String(20), nullable=True, unique=True, index=True),
        sa.Column('kanwil_id', sa.Integer(), sa.ForeignKey('kanwil.id'), nullable=True, index=True),
        sa.Column('city_id', sa.Integer(), sa.ForeignKey('city.id'), nullable=True, index=True),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lon', sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('kpp')
    op.drop_table('kanwil')
    op.drop_table('city')
    op.drop_table('province')
