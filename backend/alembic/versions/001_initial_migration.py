"""initial migration

Revision ID: 001
Revises:
Create Date: 2026-01-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pg_trgm extension
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Create user_account table
    op.create_table(
        'user_account',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('Admin', 'Analyst', 'Viewer', name='userrole'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_account_id'), 'user_account', ['id'])
    op.create_index(op.f('ix_user_account_username'), 'user_account', ['username'], unique=True)

    # Create group table
    op.create_table(
        'group',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('sector', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('extra_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_group_id'), 'group', ['id'])
    op.create_index(op.f('ix_group_name'), 'group', ['name'])
    op.execute("CREATE INDEX ix_group_name_trgm ON \"group\" USING gin (name gin_trgm_ops)")

    # Create taxpayer table
    op.create_table(
        'taxpayer',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('npwp_masked', sa.String(length=30), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('extra_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_taxpayer_id'), 'taxpayer', ['id'])
    op.create_index(op.f('ix_taxpayer_name'), 'taxpayer', ['name'])
    op.create_index(op.f('ix_taxpayer_npwp_masked'), 'taxpayer', ['npwp_masked'], unique=True)
    op.execute("CREATE INDEX ix_taxpayer_name_trgm ON taxpayer USING gin (name gin_trgm_ops)")

    # Create beneficial_owner table
    op.create_table(
        'beneficial_owner',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('id_number_masked', sa.String(length=50), nullable=True),
        sa.Column('nationality', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_beneficial_owner_id'), 'beneficial_owner', ['id'])
    op.create_index(op.f('ix_beneficial_owner_name'), 'beneficial_owner', ['name'])
    op.create_index('ix_beneficial_owner_id_number_masked', 'beneficial_owner', ['id_number_masked'], unique=True)
    op.execute("CREATE INDEX ix_beneficial_owner_name_trgm ON beneficial_owner USING gin (name gin_trgm_ops)")

    # Create group_membership table
    op.create_table(
        'group_membership',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('taxpayer_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=100), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['group.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['taxpayer_id'], ['taxpayer.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_group_membership_id'), 'group_membership', ['id'])
    op.create_index(op.f('ix_group_membership_group_id'), 'group_membership', ['group_id'])
    op.create_index(op.f('ix_group_membership_taxpayer_id'), 'group_membership', ['taxpayer_id'])
    op.create_index('ix_group_membership_composite', 'group_membership', ['group_id', 'taxpayer_id'])

    # Create beneficial_owner_taxpayer table
    op.create_table(
        'beneficial_owner_taxpayer',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('beneficial_owner_id', sa.Integer(), nullable=False),
        sa.Column('taxpayer_id', sa.Integer(), nullable=False),
        sa.Column('ownership_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.ForeignKeyConstraint(['beneficial_owner_id'], ['beneficial_owner.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['taxpayer_id'], ['taxpayer.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_beneficial_owner_taxpayer_id'), 'beneficial_owner_taxpayer', ['id'])
    op.create_index(op.f('ix_beneficial_owner_taxpayer_beneficial_owner_id'), 'beneficial_owner_taxpayer', ['beneficial_owner_id'])
    op.create_index(op.f('ix_beneficial_owner_taxpayer_taxpayer_id'), 'beneficial_owner_taxpayer', ['taxpayer_id'])

    # Create taxpayer_yearly_financial table
    op.create_table(
        'taxpayer_yearly_financial',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('taxpayer_id', sa.Integer(), nullable=False),
        sa.Column('tax_year', sa.Integer(), nullable=False),
        sa.Column('turnover', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('loss_compensation', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('spt_status', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['taxpayer_id'], ['taxpayer.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_taxpayer_yearly_financial_id'), 'taxpayer_yearly_financial', ['id'])
    op.create_index(op.f('ix_taxpayer_yearly_financial_taxpayer_id'), 'taxpayer_yearly_financial', ['taxpayer_id'])
    op.create_index(op.f('ix_taxpayer_yearly_financial_tax_year'), 'taxpayer_yearly_financial', ['tax_year'])
    op.create_index('ix_taxpayer_yearly_financial_composite', 'taxpayer_yearly_financial', ['taxpayer_id', 'tax_year'])

    # Create taxpayer_yearly_ratio table
    op.create_table(
        'taxpayer_yearly_ratio',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('taxpayer_id', sa.Integer(), nullable=False),
        sa.Column('tax_year', sa.Integer(), nullable=False),
        sa.Column('ratio_code', sa.String(length=20), nullable=False),
        sa.Column('ratio_value', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.ForeignKeyConstraint(['taxpayer_id'], ['taxpayer.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_taxpayer_yearly_ratio_id'), 'taxpayer_yearly_ratio', ['id'])
    op.create_index(op.f('ix_taxpayer_yearly_ratio_taxpayer_id'), 'taxpayer_yearly_ratio', ['taxpayer_id'])
    op.create_index(op.f('ix_taxpayer_yearly_ratio_tax_year'), 'taxpayer_yearly_ratio', ['tax_year'])
    op.create_index('ix_taxpayer_yearly_ratio_composite', 'taxpayer_yearly_ratio', ['taxpayer_id', 'tax_year', 'ratio_code'])

    # Create taxpayer_yearly_affiliate_tx table
    op.create_table(
        'taxpayer_yearly_affiliate_tx',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('taxpayer_id', sa.Integer(), nullable=False),
        sa.Column('tax_year', sa.Integer(), nullable=False),
        sa.Column('direction', sa.Enum('domestic', 'foreign', name='transactiondirection'), nullable=False),
        sa.Column('tx_type', sa.String(length=100), nullable=False),
        sa.Column('tx_value', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.ForeignKeyConstraint(['taxpayer_id'], ['taxpayer.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_taxpayer_yearly_affiliate_tx_id'), 'taxpayer_yearly_affiliate_tx', ['id'])
    op.create_index(op.f('ix_taxpayer_yearly_affiliate_tx_taxpayer_id'), 'taxpayer_yearly_affiliate_tx', ['taxpayer_id'])
    op.create_index(op.f('ix_taxpayer_yearly_affiliate_tx_tax_year'), 'taxpayer_yearly_affiliate_tx', ['tax_year'])

    # Create taxpayer_treatment_history table
    op.create_table(
        'taxpayer_treatment_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('taxpayer_id', sa.Integer(), nullable=False),
        sa.Column('treatment_date', sa.Date(), nullable=False),
        sa.Column('treatment_type', sa.String(length=100), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('outcome', sa.String(length=100), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['taxpayer_id'], ['taxpayer.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_taxpayer_treatment_history_id'), 'taxpayer_treatment_history', ['id'])
    op.create_index(op.f('ix_taxpayer_treatment_history_taxpayer_id'), 'taxpayer_treatment_history', ['taxpayer_id'])
    op.create_index(op.f('ix_taxpayer_treatment_history_treatment_date'), 'taxpayer_treatment_history', ['treatment_date'])

    # Create taxpayer_risk table
    op.create_table(
        'taxpayer_risk',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('taxpayer_id', sa.Integer(), nullable=False),
        sa.Column('tax_year', sa.Integer(), nullable=True),
        sa.Column('risk_source', sa.Enum('CRM', 'GroupEngine', 'SR', 'Other', name='risksource'), nullable=False),
        sa.Column('risk_level', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH', name='risklevel'), nullable=True),
        sa.Column('risk_score', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['taxpayer_id'], ['taxpayer.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_taxpayer_risk_id'), 'taxpayer_risk', ['id'])
    op.create_index(op.f('ix_taxpayer_risk_taxpayer_id'), 'taxpayer_risk', ['taxpayer_id'])
    op.create_index(op.f('ix_taxpayer_risk_tax_year'), 'taxpayer_risk', ['tax_year'])

    # Create audit_log table
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('actor_user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('payload', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['actor_user_id'], ['user_account.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_log_id'), 'audit_log', ['id'])
    op.create_index(op.f('ix_audit_log_actor_user_id'), 'audit_log', ['actor_user_id'])
    op.create_index(op.f('ix_audit_log_action'), 'audit_log', ['action'])
    op.create_index(op.f('ix_audit_log_timestamp'), 'audit_log', ['timestamp'])

    # Create user_recent_view table
    op.create_table(
        'user_recent_view',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('last_viewed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user_account.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_recent_view_id'), 'user_recent_view', ['id'])
    op.create_index(op.f('ix_user_recent_view_user_id'), 'user_recent_view', ['user_id'])
    op.create_index(op.f('ix_user_recent_view_last_viewed_at'), 'user_recent_view', ['last_viewed_at'])


def downgrade() -> None:
    op.drop_table('user_recent_view')
    op.drop_table('audit_log')
    op.drop_table('taxpayer_risk')
    op.drop_table('taxpayer_treatment_history')
    op.drop_table('taxpayer_yearly_affiliate_tx')
    op.drop_table('taxpayer_yearly_ratio')
    op.drop_table('taxpayer_yearly_financial')
    op.drop_table('beneficial_owner_taxpayer')
    op.drop_table('group_membership')
    op.drop_table('beneficial_owner')
    op.drop_table('taxpayer')
    op.drop_table('group')
    op.drop_table('user_account')
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
