from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class TaxpayerYearlyFinancial(Base):
    __tablename__ = "taxpayer_yearly_financial"

    id = Column(Integer, primary_key=True, index=True)
    taxpayer_id = Column(Integer, ForeignKey("taxpayer.id", ondelete="CASCADE"), nullable=False, index=True)
    tax_year = Column(Integer, nullable=False, index=True)
    turnover = Column(Numeric(20, 2), nullable=True)  # Omset
    loss_compensation = Column(Numeric(20, 2), nullable=True)  # Kompensasi kerugian
    spt_status = Column(String(50), nullable=True)  # e.g., "Sudah Lapor", "Belum Lapor", "Pembetulan"

    # Relationships
    taxpayer = relationship("Taxpayer", back_populates="yearly_financials")
