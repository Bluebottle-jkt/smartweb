"""add derived groups and relationships

Revision ID: 002
Revises: 001
Create Date: 2026-01-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums
    entity_type_enum = postgresql.ENUM('TAXPAYER', 'BENEFICIAL_OWNER', 'ENTITY', name='entitytype', create_type=False)
    entity_type_enum.create(op.get_bind(), checkfirst=True)

    relationship_type_enum = postgresql.ENUM('OWNERSHIP', 'CONTROL', 'FAMILY', 'AFFILIATION_OTHER', name='relationshiptype', create_type=False)
    relationship_type_enum.create(op.get_bind(), checkfirst=True)

    # Create relationship table
    op.create_table(
        'relationship',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('from_entity_type', entity_type_enum, nullable=False),
        sa.Column('from_entity_id', sa.Integer(), nullable=False),
        sa.Column('to_entity_type', entity_type_enum, nullable=False),
        sa.Column('to_entity_id', sa.Integer(), nullable=False),
        sa.Column('relationship_type', relationship_type_enum, nullable=False),
        sa.Column('pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('source', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_relationship_id'), 'relationship', ['id'])
    op.create_index(op.f('ix_relationship_from_entity_type'), 'relationship', ['from_entity_type'])
    op.create_index(op.f('ix_relationship_from_entity_id'), 'relationship', ['from_entity_id'])
    op.create_index(op.f('ix_relationship_to_entity_type'), 'relationship', ['to_entity_type'])
    op.create_index(op.f('ix_relationship_to_entity_id'), 'relationship', ['to_entity_id'])
    op.create_index(op.f('ix_relationship_relationship_type'), 'relationship', ['relationship_type'])
    op.create_index(op.f('ix_relationship_effective_from'), 'relationship', ['effective_from'])
    op.create_index(op.f('ix_relationship_effective_to'), 'relationship', ['effective_to'])
    op.create_index('ix_relationship_composite_from', 'relationship', ['from_entity_type', 'from_entity_id'])
    op.create_index('ix_relationship_composite_to', 'relationship', ['to_entity_type', 'to_entity_id'])

    # Create group_definition_rule_set table
    op.create_table(
        'group_definition_rule_set',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=False, nullable=False),
        sa.Column('min_members', sa.Integer(), default=2, nullable=False),
        sa.Column('max_hops', sa.Integer(), default=4, nullable=False),
        sa.Column('as_of_date', sa.Date(), nullable=True),
        sa.Column('direct_ownership_threshold_pct', sa.Numeric(precision=5, scale=2), default=25, nullable=False),
        sa.Column('indirect_ownership_threshold_pct', sa.Numeric(precision=5, scale=2), default=25, nullable=False),
        sa.Column('include_relationship_types', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('control_as_affiliation', sa.Boolean(), default=True, nullable=False),
        sa.Column('min_confidence', sa.Numeric(precision=3, scale=2), default=0.0, nullable=False),
        sa.Column('bo_shared_any', sa.Boolean(), default=True, nullable=False),
        sa.Column('bo_shared_min_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_group_definition_rule_set_id'), 'group_definition_rule_set', ['id'])
    op.create_index(op.f('ix_group_definition_rule_set_is_active'), 'group_definition_rule_set', ['is_active'])

    # Create derived_group table
    op.create_table(
        'derived_group',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_set_id', sa.Integer(), nullable=False),
        sa.Column('group_key', sa.String(length=100), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('as_of_date', sa.Date(), nullable=True),
        sa.Column('summary', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['rule_set_id'], ['group_definition_rule_set.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_key')
    )
    op.create_index(op.f('ix_derived_group_id'), 'derived_group', ['id'])
    op.create_index(op.f('ix_derived_group_rule_set_id'), 'derived_group', ['rule_set_id'])
    op.create_index(op.f('ix_derived_group_generated_at'), 'derived_group', ['generated_at'])

    # Create derived_group_membership table
    op.create_table(
        'derived_group_membership',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('derived_group_id', sa.Integer(), nullable=False),
        sa.Column('taxpayer_id', sa.Integer(), nullable=False),
        sa.Column('strength_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('evidence', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['derived_group_id'], ['derived_group.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['taxpayer_id'], ['taxpayer.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('derived_group_id', 'taxpayer_id', name='uq_derived_group_taxpayer')
    )
    op.create_index(op.f('ix_derived_group_membership_id'), 'derived_group_membership', ['id'])
    op.create_index(op.f('ix_derived_group_membership_derived_group_id'), 'derived_group_membership', ['derived_group_id'])
    op.create_index(op.f('ix_derived_group_membership_taxpayer_id'), 'derived_group_membership', ['taxpayer_id'])


def downgrade() -> None:
    op.drop_table('derived_group_membership')
    op.drop_table('derived_group')
    op.drop_table('group_definition_rule_set')
    op.drop_table('relationship')

    # Drop enums
    relationship_type_enum = postgresql.ENUM('OWNERSHIP', 'CONTROL', 'FAMILY', 'AFFILIATION_OTHER', name='relationshiptype', create_type=False)
    relationship_type_enum.drop(op.get_bind(), checkfirst=True)

    entity_type_enum = postgresql.ENUM('TAXPAYER', 'BENEFICIAL_OWNER', 'ENTITY', name='entitytype', create_type=False)
    entity_type_enum.drop(op.get_bind(), checkfirst=True)
