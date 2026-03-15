"""
EntitySearchIndex – unified denormalised search index.
DatasetVersion    – ingestion run history.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TSVECTOR

from app.db.base import Base


class EntitySearchIndex(Base):
    __tablename__ = "entity_search_index"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    entity_type     = Column(String(30),  nullable=False, index=True)
    entity_id       = Column(Integer,     nullable=False)
    name            = Column(String(500), nullable=False)
    normalized_name = Column(String(500), nullable=True)
    npwp            = Column(String(30),  nullable=True, index=True)
    entity_subtype  = Column(String(100), nullable=True)
    status          = Column(String(30),  nullable=True)
    city            = Column(String(200), nullable=True)
    kpp_name        = Column(String(200), nullable=True)
    kanwil_name     = Column(String(200), nullable=True)
    nationality     = Column(String(100), nullable=True)
    search_vector   = Column(TSVECTOR,    nullable=True)
    rank_score      = Column(Float,       nullable=True, default=1.0)
    updated_at      = Column(DateTime(timezone=True),
                             default=lambda: datetime.now(timezone.utc),
                             onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('entity_type', 'entity_id', name='uq_entity_search_index_type_id'),
    )


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id                      = Column(Integer,  primary_key=True, autoincrement=True)
    version_tag             = Column(String(64), nullable=False, unique=True)
    source_file             = Column(String(500), nullable=True)
    source_type             = Column(String(30),  nullable=True)   # CSV | PARQUET | POSTGRES
    schema_hash             = Column(String(64),  nullable=True)
    record_count            = Column(Integer,     nullable=True)
    entity_count            = Column(Integer,     nullable=True)
    relationship_count      = Column(Integer,     nullable=True)
    status                  = Column(String(20),  nullable=False, default='PENDING')
    error_message           = Column(Text,        nullable=True)
    ingested_by             = Column(String(100), nullable=True)
    ingestion_started_at    = Column(DateTime(timezone=True), nullable=True)
    ingestion_completed_at  = Column(DateTime(timezone=True), nullable=True)
    created_at              = Column(DateTime(timezone=True),
                                     default=lambda: datetime.now(timezone.utc))
