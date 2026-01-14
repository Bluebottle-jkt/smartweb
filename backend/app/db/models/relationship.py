from sqlalchemy import Column, Integer, String, Numeric, Date, Text, DateTime, Enum
from sqlalchemy.sql import func
import enum
from app.db.base import Base
from app.db.models.enum_utils import enum_values


class EntityType(str, enum.Enum):
    TAXPAYER = "TAXPAYER"
    BENEFICIAL_OWNER = "BENEFICIAL_OWNER"
    ENTITY = "ENTITY"


class RelationshipType(str, enum.Enum):
    OWNERSHIP = "OWNERSHIP"
    CONTROL = "CONTROL"
    FAMILY = "FAMILY"
    AFFILIATION_OTHER = "AFFILIATION_OTHER"


class Relationship(Base):
    __tablename__ = "relationship"

    id = Column(Integer, primary_key=True, index=True)
    from_entity_type = Column(Enum(EntityType, values_callable=enum_values), nullable=False, index=True)
    from_entity_id = Column(Integer, nullable=False, index=True)
    to_entity_type = Column(Enum(EntityType, values_callable=enum_values), nullable=False, index=True)
    to_entity_id = Column(Integer, nullable=False, index=True)
    relationship_type = Column(Enum(RelationshipType, values_callable=enum_values), nullable=False, index=True)
    pct = Column(Numeric(5, 2), nullable=True)  # 0-100 for OWNERSHIP
    effective_from = Column(Date, nullable=True, index=True)
    effective_to = Column(Date, nullable=True, index=True)
    source = Column(Text, nullable=True)
    confidence = Column(Numeric(3, 2), nullable=True)  # 0-1
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
