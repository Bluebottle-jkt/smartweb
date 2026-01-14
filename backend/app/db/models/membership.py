from sqlalchemy import Column, Integer, String, Date, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.db.base import Base


class GroupMembership(Base):
    __tablename__ = "group_membership"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("group.id", ondelete="CASCADE"), nullable=False, index=True)
    taxpayer_id = Column(Integer, ForeignKey("taxpayer.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(100), nullable=True)  # e.g., Parent, Subsidiary, Affiliate
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    # Relationships
    group = relationship("Group", back_populates="memberships")
    taxpayer = relationship("Taxpayer", back_populates="memberships")


class BeneficialOwnerTaxpayer(Base):
    __tablename__ = "beneficial_owner_taxpayer"

    id = Column(Integer, primary_key=True, index=True)
    beneficial_owner_id = Column(Integer, ForeignKey("beneficial_owner.id", ondelete="CASCADE"), nullable=False, index=True)
    taxpayer_id = Column(Integer, ForeignKey("taxpayer.id", ondelete="CASCADE"), nullable=False, index=True)
    ownership_pct = Column(Numeric(5, 2), nullable=True)  # Percentage, e.g., 25.50

    # Relationships
    beneficial_owner = relationship("BeneficialOwner", back_populates="taxpayers")
    taxpayer = relationship("Taxpayer", back_populates="beneficial_owners")
