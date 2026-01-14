from sqlalchemy import Column, Integer, String, Boolean, Numeric, Date, DateTime, Text, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class GroupDefinitionRuleSet(Base):
    __tablename__ = "group_definition_rule_set"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    min_members = Column(Integer, default=2, nullable=False)
    max_hops = Column(Integer, default=4, nullable=False)
    as_of_date = Column(Date, nullable=True)
    direct_ownership_threshold_pct = Column(Numeric(5, 2), default=25, nullable=False)
    indirect_ownership_threshold_pct = Column(Numeric(5, 2), default=25, nullable=False)
    include_relationship_types = Column(ARRAY(String), default=['OWNERSHIP', 'CONTROL'], nullable=False)
    control_as_affiliation = Column(Boolean, default=True, nullable=False)
    min_confidence = Column(Numeric(3, 2), default=0.0, nullable=False)
    bo_shared_any = Column(Boolean, default=True, nullable=False)
    bo_shared_min_pct = Column(Numeric(5, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    derived_groups = relationship("DerivedGroup", back_populates="rule_set", cascade="all, delete-orphan")
