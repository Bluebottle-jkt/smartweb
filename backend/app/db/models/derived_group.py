from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, JSON, Numeric, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class DerivedGroup(Base):
    __tablename__ = "derived_group"

    id = Column(Integer, primary_key=True, index=True)
    rule_set_id = Column(Integer, ForeignKey("group_definition_rule_set.id", ondelete="CASCADE"), nullable=False, index=True)
    group_key = Column(String(100), unique=True, nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    as_of_date = Column(Date, nullable=True)
    summary = Column(JSON, nullable=True)

    # Relationships
    rule_set = relationship("GroupDefinitionRuleSet", back_populates="derived_groups")
    memberships = relationship("DerivedGroupMembership", back_populates="derived_group", cascade="all, delete-orphan")


class DerivedGroupMembership(Base):
    __tablename__ = "derived_group_membership"

    id = Column(Integer, primary_key=True, index=True)
    derived_group_id = Column(Integer, ForeignKey("derived_group.id", ondelete="CASCADE"), nullable=False, index=True)
    taxpayer_id = Column(Integer, ForeignKey("taxpayer.id", ondelete="CASCADE"), nullable=False, index=True)
    strength_score = Column(Numeric(5, 2), nullable=True)  # 0-100
    evidence = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    derived_group = relationship("DerivedGroup", back_populates="memberships")
    taxpayer = relationship("Taxpayer")

    __table_args__ = (
        UniqueConstraint('derived_group_id', 'taxpayer_id', name='uq_derived_group_taxpayer'),
    )
