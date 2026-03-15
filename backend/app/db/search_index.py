"""
Entity Search Index helpers.

`refresh_entity_search_index(db)` performs a full UPSERT of all
Taxpayer, BeneficialOwner, Group, and Officer rows into the
entity_search_index table, then updates tsvector search vectors.

This is idempotent and safe to run on every startup.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.models import BeneficialOwner, Group, Officer, Taxpayer
from app.db.models.search_index import EntitySearchIndex


def _normalize(s: str) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s.lower()).strip()


def _extract_city(address: Optional[str]) -> Optional[str]:
    if not address:
        return None
    parts = [p.strip() for p in address.split(",")]
    return parts[-2] if len(parts) >= 2 else parts[-1] if parts else None


def _upsert(db: Session, entity_type: str, entity_id: int, **kwargs) -> None:
    existing = (
        db.query(EntitySearchIndex)
        .filter_by(entity_type=entity_type, entity_id=entity_id)
        .first()
    )
    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
        existing.updated_at = datetime.now(timezone.utc)
    else:
        db.add(EntitySearchIndex(entity_type=entity_type, entity_id=entity_id, **kwargs))


def refresh_entity_search_index(db: Session) -> dict:
    """
    Full rebuild of entity_search_index from live ORM tables.
    Returns counts dict.
    """
    counts: dict = {"taxpayers": 0, "bos": 0, "groups": 0, "officers": 0}

    # ── Taxpayers ────────────────────────────────────────────────────────
    for tp in db.query(Taxpayer).yield_per(500):
        _upsert(
            db, "TAXPAYER", tp.id,
            name=tp.name,
            normalized_name=_normalize(tp.name),
            npwp=getattr(tp, "npwp_masked", None),
            entity_subtype=getattr(tp, "entity_type", None),
            status=getattr(tp, "status", None),
            city=_extract_city(getattr(tp, "address", None)),
            rank_score=1.0,
        )
        counts["taxpayers"] += 1

    # ── Beneficial Owners ─────────────────────────────────────────────────
    for bo in db.query(BeneficialOwner).yield_per(500):
        _upsert(
            db, "BENEFICIAL_OWNER", bo.id,
            name=bo.name,
            normalized_name=_normalize(bo.name),
            nationality=getattr(bo, "nationality", None),
            rank_score=0.8,
        )
        counts["bos"] += 1

    # ── Groups ────────────────────────────────────────────────────────────
    for g in db.query(Group).yield_per(500):
        _upsert(
            db, "GROUP", g.id,
            name=g.name,
            normalized_name=_normalize(g.name),
            rank_score=0.75,
        )
        counts["groups"] += 1

    # ── Officers ──────────────────────────────────────────────────────────
    for o in db.query(Officer).yield_per(500):
        _upsert(
            db, "OFFICER", o.id,
            name=o.name,
            normalized_name=_normalize(o.name),
            entity_subtype=getattr(o, "position", None),
            rank_score=0.7,
        )
        counts["officers"] += 1

    db.flush()

    # Update tsvector search vectors in bulk via raw SQL
    try:
        db.execute(text("""
            UPDATE entity_search_index
            SET search_vector = to_tsvector('simple', coalesce(name, '') || ' ' || coalesce(normalized_name, '') || ' ' || coalesce(npwp, ''))
        """))
    except Exception:
        pass  # pg_trgm may not be enabled yet

    db.commit()
    return counts
