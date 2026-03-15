"""
PostgreSQL models for Graph Intelligence results.

These tables store detection outputs, risk signals, and graph sync state so
results can be cached, audited, and surfaced in the UI without re-running
expensive algorithms on every request.
"""
from __future__ import annotations

import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.models.enum_utils import enum_values


class DetectionType(str, enum.Enum):
    OWNERSHIP_PYRAMID = "OWNERSHIP_PYRAMID"
    CIRCULAR_TRANSACTION = "CIRCULAR_TRANSACTION"
    BENEFICIAL_OWNER_INFERENCE = "BENEFICIAL_OWNER_INFERENCE"
    VAT_CAROUSEL = "VAT_CAROUSEL"
    TRADE_MISPRICING = "TRADE_MISPRICING"
    SHELL_COMPANY = "SHELL_COMPANY"
    NOMINEE_DIRECTOR = "NOMINEE_DIRECTOR"
    AI_DISCOVERY = "AI_DISCOVERY"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class GraphSyncState(Base):
    """Tracks Neo4j synchronisation progress per entity."""
    __tablename__ = "graph_sync_state"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    sync_status = Column(String(20), nullable=False, default="PENDING")  # PENDING / OK / ERROR
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", name="uq_graph_sync_entity"),
    )


class GraphDetectionResult(Base):
    """
    Stores the output of a graph intelligence detector run for a given entity
    and year.  Results are immutable snapshots – re-runs create new rows.
    """
    __tablename__ = "graph_detection_result"

    id = Column(Integer, primary_key=True, index=True)
    detection_type = Column(
        Enum(DetectionType, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    # Primary subject (root NPWP / entity)
    root_npwp = Column(String(30), nullable=False, index=True)
    root_entity_type = Column(String(50), nullable=False)
    root_entity_id = Column(Integer, nullable=True, index=True)
    tax_year = Column(Integer, nullable=True, index=True)

    # Risk output
    risk_level = Column(Enum(RiskLevel, values_callable=enum_values), nullable=True)
    risk_score = Column(Float, nullable=True)          # 0.0 – 1.0
    confidence_score = Column(Float, nullable=True)    # 0.0 – 1.0

    # Human-readable explanation
    summary = Column(Text, nullable=True)
    reason_codes = Column(JSON, nullable=True)          # list[str]

    # Structured evidence payload (entity lists, paths, amounts, etc.)
    evidence = Column(JSON, nullable=True)

    # Who triggered it
    triggered_by_user_id = Column(Integer, ForeignKey("user_account.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class GraphRiskSignal(Base):
    """
    Individual risk signals attached to entities.  Multiple signals per entity,
    per detection run.  Supports incremental enrichment.
    """
    __tablename__ = "graph_risk_signal"

    id = Column(Integer, primary_key=True, index=True)
    detection_result_id = Column(
        Integer, ForeignKey("graph_detection_result.id", ondelete="CASCADE"), nullable=True
    )
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    entity_npwp = Column(String(30), nullable=True)
    signal_code = Column(String(100), nullable=False, index=True)
    signal_value = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EntitySubstanceProfile(Base):
    """
    Composite substance metrics for an entity used by shell/nominee detectors.
    Populated from seed/financial data and refreshed on sync.
    """
    __tablename__ = "entity_substance_profile"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)
    tax_year = Column(Integer, nullable=False)

    # Substance indicators (0 = absent, 1 = strong)
    officer_count = Column(Integer, nullable=True, default=0)
    director_count = Column(Integer, nullable=True, default=0)
    address_count = Column(Integer, nullable=True, default=0)
    shared_address_entity_count = Column(Integer, nullable=True, default=0)
    turnover = Column(Float, nullable=True)
    tax_paid = Column(Float, nullable=True)
    affiliate_tx_total = Column(Float, nullable=True)
    ownership_opacity_score = Column(Float, nullable=True)  # 0–1

    # Composite shell score (0 = clean, 1 = likely shell)
    shell_risk_score = Column(Float, nullable=True)
    nominee_risk_score = Column(Float, nullable=True)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("entity_id", "entity_type", "tax_year", name="uq_substance_profile"),
    )
