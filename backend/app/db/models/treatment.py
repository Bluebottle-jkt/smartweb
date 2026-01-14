from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class TaxpayerTreatmentHistory(Base):
    __tablename__ = "taxpayer_treatment_history"

    id = Column(Integer, primary_key=True, index=True)
    taxpayer_id = Column(Integer, ForeignKey("taxpayer.id", ondelete="CASCADE"), nullable=False, index=True)
    treatment_date = Column(Date, nullable=False, index=True)
    treatment_type = Column(String(100), nullable=False)  # e.g., "SP2DK", "Klarifikasi", "Pemeriksaan", "Himbauan"
    notes = Column(Text, nullable=True)
    outcome = Column(String(100), nullable=True)  # e.g., "Selesai", "Berlanjut", "Tidak Ada Koreksi"
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    taxpayer = relationship("Taxpayer", back_populates="treatment_histories")
