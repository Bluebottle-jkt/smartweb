from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # e.g., "CREATE", "UPDATE", "DELETE", "EXPORT"
    entity_type = Column(String(50), nullable=False)  # e.g., "Group", "Taxpayer", "BeneficialOwner"
    entity_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    payload = Column(JSON, nullable=True)  # Additional context data
