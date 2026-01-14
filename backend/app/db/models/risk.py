from sqlalchemy import Column, Integer, String, Text, Numeric, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base
from app.db.models.enum_utils import enum_values


class RiskSource(str, enum.Enum):
    CRM = "CRM"
    GROUP_ENGINE = "GroupEngine"
    SR = "SR"
    OTHER = "Other"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class TaxpayerRisk(Base):
    __tablename__ = "taxpayer_risk"

    id = Column(Integer, primary_key=True, index=True)
    taxpayer_id = Column(Integer, ForeignKey("taxpayer.id", ondelete="CASCADE"), nullable=False, index=True)
    tax_year = Column(Integer, nullable=True, index=True)
    risk_source = Column(Enum(RiskSource, values_callable=enum_values), nullable=False)
    risk_level = Column(Enum(RiskLevel, values_callable=enum_values), nullable=True)
    risk_score = Column(Numeric(10, 2), nullable=True)  # For numerical scores like GroupEngine
    notes = Column(Text, nullable=True)

    # Relationships
    taxpayer = relationship("Taxpayer", back_populates="risks")
