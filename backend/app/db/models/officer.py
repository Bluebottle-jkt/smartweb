from sqlalchemy import Column, Integer, String, Text, DateTime, Date
from sqlalchemy.sql import func
from app.db.base import Base


class Officer(Base):
    """Officer entity - Directors, Commissioners, and other corporate officers."""
    __tablename__ = "officer"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    id_number_masked = Column(String(50), nullable=True, unique=True)
    position = Column(String(100), nullable=True)  # e.g., Direktur Utama, Komisaris
    nationality = Column(String(100), nullable=True)
    birth_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
