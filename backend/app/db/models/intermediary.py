from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.db.base import Base


class Intermediary(Base):
    """Intermediary entity - Law firms, accountants, agents facilitating company formation."""
    __tablename__ = "intermediary"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    intermediary_type = Column(String(100), nullable=True)  # e.g., Law Firm, Accounting Firm, Agent
    country = Column(String(100), nullable=True, index=True)
    status = Column(String(50), nullable=True)  # e.g., Active, Inactive
    address = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
