from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.sql import func
from app.db.base import Base


class Address(Base):
    """Address entity - Physical locations linked to taxpayers and officers."""
    __tablename__ = "address"

    id = Column(Integer, primary_key=True, index=True)
    full_address = Column(Text, nullable=False)
    street = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True, index=True)
    province = Column(String(100), nullable=True, index=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=False, default="Indonesia")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address_type = Column(String(50), nullable=True)  # e.g., Kantor Pusat, Cabang, Gudang
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
