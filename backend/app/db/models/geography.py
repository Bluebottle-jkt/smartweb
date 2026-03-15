"""
Geography master data: Province → Kanwil DJP → KPP → City

Used by:
- Peta Sebaran Group (circle-marker map)
- Statistik DJP (Kanwil / KPP drill-down)
- Entity autocomplete (enrich suggestions with location context)
"""
from __future__ import annotations

from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class Province(Base):
    __tablename__ = "province"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    code = Column(String(10), nullable=True)
    # Cities in this province
    cities = relationship("City", back_populates="province", lazy="select")
    # Kanwil in this province (1 Kanwil can span multiple provinces but this is simplified)
    kanwils = relationship("Kanwil", back_populates="province", lazy="select")


class City(Base):
    """Kabupaten/Kota – level 2 administrative area."""
    __tablename__ = "city"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    province_id = Column(Integer, ForeignKey("province.id"), nullable=True, index=True)
    lat = Column(Float, nullable=True)   # WGS-84 latitude
    lon = Column(Float, nullable=True)   # WGS-84 longitude

    province = relationship("Province", back_populates="cities")
    kpps = relationship("KPP", back_populates="city", lazy="select")


class Kanwil(Base):
    """
    Kantor Wilayah DJP – regional tax office.
    There are ~34 Kanwil DJP across Indonesia.
    """
    __tablename__ = "kanwil"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, unique=True, index=True)
    code = Column(String(20), nullable=True, unique=True)
    province_id = Column(Integer, ForeignKey("province.id"), nullable=True, index=True)
    # Representative coordinates for map marker
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)

    province = relationship("Province", back_populates="kanwils")
    kpps = relationship("KPP", back_populates="kanwil", lazy="select")


class KPP(Base):
    """
    Kantor Pelayanan Pajak – local tax service office.
    Each KPP belongs to a Kanwil.  Taxpayers are registered at a KPP.
    """
    __tablename__ = "kpp"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    code = Column(String(20), nullable=True, unique=True, index=True)
    kanwil_id = Column(Integer, ForeignKey("kanwil.id"), nullable=True, index=True)
    city_id = Column(Integer, ForeignKey("city.id"), nullable=True, index=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)

    kanwil = relationship("Kanwil", back_populates="kpps")
    city = relationship("City", back_populates="kpps")
