from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class BeneficialOwner(Base):
    __tablename__ = "beneficial_owner"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    id_number_masked = Column(String(50), nullable=True, unique=True)
    nationality = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    taxpayers = relationship("BeneficialOwnerTaxpayer", back_populates="beneficial_owner", cascade="all, delete-orphan")
