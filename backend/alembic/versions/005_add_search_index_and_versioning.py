"""Add entity_search_index and dataset_versions tables

Revision ID: 005_add_search_index
Revises: 004_add_geography
Create Date: 2026-03-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '005_add_search_index'
down_revision = '004_add_geography'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── entity_search_index ────────────────────────────────────────────────
    # Unified, denormalised search index used by /entities/suggest.
    # Refreshed on seed / ingestion. Supports pg_trgm similarity + GIN FTS.
    op.create_table(
        'entity_search_index',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('entity_type', sa.String(30), nullable=False, index=True),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('normalized_name', sa.String(500), nullable=True),
        sa.Column('npwp', sa.String(30), nullable=True, index=True),
        sa.Column('entity_subtype', sa.String(100), nullable=True),
        sa.Column('status', sa.String(30), nullable=True),
        sa.Column('city', sa.String(200), nullable=True),
        sa.Column('kpp_name', sa.String(200), nullable=True),
        sa.Column('kanwil_name', sa.String(200), nullable=True),
        sa.Column('nationality', sa.String(100), nullable=True),
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
        sa.Column('rank_score', sa.Float(), nullable=True, server_default='1.0'),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )

    # Composite unique: one row per (entity_type, entity_id)
    op.create_unique_constraint(
        'uq_entity_search_index_type_id',
        'entity_search_index',
        ['entity_type', 'entity_id'],
    )

    # GIN index for full-text search vector
    op.create_index(
        'ix_entity_search_index_search_vector',
        'entity_search_index',
        ['search_vector'],
        postgresql_using='gin',
    )

    # pg_trgm trigram index on normalized_name for fuzzy matching
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_entity_search_index_trgm "
        "ON entity_search_index USING gin (normalized_name gin_trgm_ops)"
    )

    # ── dataset_versions ──────────────────────────────────────────────────
    # Records every ingestion run so history and rollback are possible.
    op.create_table(
        'dataset_versions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('version_tag', sa.String(64), nullable=False, unique=True),
        sa.Column('source_file', sa.String(500), nullable=True),
        sa.Column('source_type', sa.String(30), nullable=True),   # CSV, PARQUET, POSTGRES
        sa.Column('schema_hash', sa.String(64), nullable=True),
        sa.Column('record_count', sa.Integer(), nullable=True),
        sa.Column('entity_count', sa.Integer(), nullable=True),
        sa.Column('relationship_count', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('ingested_by', sa.String(100), nullable=True),
        sa.Column('ingestion_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ingestion_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )

    op.create_index(
        'ix_dataset_versions_created_at',
        'dataset_versions',
        ['created_at'],
    )
    op.create_index(
        'ix_dataset_versions_status',
        'dataset_versions',
        ['status'],
    )


def downgrade() -> None:
    op.drop_index('ix_dataset_versions_status', table_name='dataset_versions')
    op.drop_index('ix_dataset_versions_created_at', table_name='dataset_versions')
    op.drop_table('dataset_versions')

    op.execute("DROP INDEX IF EXISTS ix_entity_search_index_trgm")
    op.drop_index('ix_entity_search_index_search_vector', table_name='entity_search_index')
    op.drop_constraint('uq_entity_search_index_type_id', 'entity_search_index', type_='unique')
    op.drop_table('entity_search_index')
