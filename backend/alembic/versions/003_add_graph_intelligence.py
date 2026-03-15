"""Add graph intelligence tables

Revision ID: 003_add_graph_intelligence
Revises: 6fc5383b6719
Create Date: 2026-03-14

"""
from alembic import op
import sqlalchemy as sa

revision = '003_add_graph_intelligence'
down_revision = '6fc5383b6719'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- graph_sync_state ---------------------------------------------------
    op.create_table(
        'graph_sync_state',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('entity_type', sa.String(50), nullable=False, index=True),
        sa.Column('entity_id', sa.Integer(), nullable=False, index=True),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('entity_type', 'entity_id', name='uq_graph_sync_entity'),
    )

    # --- graph_detection_result ---------------------------------------------
    detection_type_enum = sa.Enum(
        'OWNERSHIP_PYRAMID', 'CIRCULAR_TRANSACTION', 'BENEFICIAL_OWNER_INFERENCE',
        'VAT_CAROUSEL', 'TRADE_MISPRICING', 'SHELL_COMPANY', 'NOMINEE_DIRECTOR', 'AI_DISCOVERY',
        name='detectiontype',
    )
    risk_level_enum = sa.Enum(
        'LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH',
        name='graph_risk_level',
    )
    op.create_table(
        'graph_detection_result',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('detection_type', detection_type_enum, nullable=False, index=True),
        sa.Column('root_npwp', sa.String(30), nullable=False, index=True),
        sa.Column('root_entity_type', sa.String(50), nullable=False),
        sa.Column('root_entity_id', sa.Integer(), nullable=True, index=True),
        sa.Column('tax_year', sa.Integer(), nullable=True, index=True),
        sa.Column('risk_level', risk_level_enum, nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('reason_codes', sa.JSON(), nullable=True),
        sa.Column('evidence', sa.JSON(), nullable=True),
        sa.Column('triggered_by_user_id', sa.Integer(), sa.ForeignKey('user_account.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    # --- graph_risk_signal --------------------------------------------------
    op.create_table(
        'graph_risk_signal',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('detection_result_id', sa.Integer(),
                  sa.ForeignKey('graph_detection_result.id', ondelete='CASCADE'), nullable=True),
        sa.Column('entity_type', sa.String(50), nullable=False, index=True),
        sa.Column('entity_id', sa.Integer(), nullable=False, index=True),
        sa.Column('entity_npwp', sa.String(30), nullable=True),
        sa.Column('signal_code', sa.String(100), nullable=False, index=True),
        sa.Column('signal_value', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- entity_substance_profile -------------------------------------------
    op.create_table(
        'entity_substance_profile',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('entity_id', sa.Integer(), nullable=False, index=True),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('tax_year', sa.Integer(), nullable=False),
        sa.Column('officer_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('director_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('address_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('shared_address_entity_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('turnover', sa.Float(), nullable=True),
        sa.Column('tax_paid', sa.Float(), nullable=True),
        sa.Column('affiliate_tx_total', sa.Float(), nullable=True),
        sa.Column('ownership_opacity_score', sa.Float(), nullable=True),
        sa.Column('shell_risk_score', sa.Float(), nullable=True),
        sa.Column('nominee_risk_score', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('entity_id', 'entity_type', 'tax_year', name='uq_substance_profile'),
    )


def downgrade() -> None:
    op.drop_table('entity_substance_profile')
    op.drop_table('graph_risk_signal')
    op.drop_table('graph_detection_result')
    op.drop_table('graph_sync_state')
    sa.Enum(name='graph_risk_level').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='detectiontype').drop(op.get_bind(), checkfirst=True)
