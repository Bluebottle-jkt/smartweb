from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Taxpayer(Base):
    __tablename__ = "taxpayer"

    id = Column(Integer, primary_key=True, index=True)
    npwp_masked = Column(String(30), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    entity_type = Column(String(50), nullable=True)  # e.g., PT, CV, UD, Perorangan
    address = Column(Text, nullable=True)
    status = Column(String(50), nullable=True)  # e.g., Aktif, Non-Aktif
    extra_metadata = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    memberships = relationship("GroupMembership", back_populates="taxpayer", cascade="all, delete-orphan")
    beneficial_owners = relationship("BeneficialOwnerTaxpayer", back_populates="taxpayer", cascade="all, delete-orphan")
    yearly_financials = relationship("TaxpayerYearlyFinancial", back_populates="taxpayer", cascade="all, delete-orphan")
    yearly_ratios = relationship("TaxpayerYearlyRatio", back_populates="taxpayer", cascade="all, delete-orphan")
    yearly_affiliate_txs = relationship("TaxpayerYearlyAffiliateTx", back_populates="taxpayer", cascade="all, delete-orphan")
    treatment_histories = relationship("TaxpayerTreatmentHistory", back_populates="taxpayer", cascade="all, delete-orphan")
    risks = relationship("TaxpayerRisk", back_populates="taxpayer", cascade="all, delete-orphan")
