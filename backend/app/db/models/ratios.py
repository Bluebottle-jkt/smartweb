from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class TaxpayerYearlyRatio(Base):
    __tablename__ = "taxpayer_yearly_ratio"

    id = Column(Integer, primary_key=True, index=True)
    taxpayer_id = Column(Integer, ForeignKey("taxpayer.id", ondelete="CASCADE"), nullable=False, index=True)
    tax_year = Column(Integer, nullable=False, index=True)
    ratio_code = Column(String(20), nullable=False)  # e.g., "CTTOR", "ETR", "NPM"
    ratio_value = Column(Numeric(10, 4), nullable=True)

    # Relationships
    taxpayer = relationship("Taxpayer", back_populates="yearly_ratios")
