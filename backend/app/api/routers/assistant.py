"""
Chat Assistant – Entity Discovery Router

A rule-based retrieval assistant that helps users find whether a taxpayer,
beneficial owner, or other entity already exists in the SmartWeb database,
and returns a direct graph link when found.

Supports queries like:
- "Apakah PT ABC ada di database?"
- "Cari NPWP 01.234.567.8-999.000"
- "Andi Pratama"
"""
from __future__ import annotations

import re
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import BeneficialOwner, Group, Officer, Taxpayer, UserAccount
from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assistant", tags=["assistant"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AssistantQuery(BaseModel):
    query: str
    limit: int = 5


class MatchedEntity(BaseModel):
    entity_type: str
    id: int
    name: str
    npwp: Optional[str] = None
    entity_subtype: Optional[str] = None
    status: Optional[str] = None
    nationality: Optional[str] = None
    graph_url: Optional[str] = None
    confidence: float = 1.0


class AssistantResponse(BaseModel):
    query: str
    intent: str          # NPWP_SEARCH | NAME_SEARCH | GENERAL
    found: bool
    match_count: int
    entities: List[MatchedEntity]
    message: str
    timestamp: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/entity-discovery", response_model=AssistantResponse)
def entity_discovery(
    body: AssistantQuery,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    """
    Natural-language-style entity discovery endpoint.
    Detects whether the query contains an NPWP pattern and routes accordingly.
    Falls back to fuzzy name search if no NPWP detected.
    """
    query_text = body.query.strip()
    entities: List[MatchedEntity] = []
    intent = "NAME_SEARCH"

    # Detect NPWP pattern (15 digits, possibly formatted with . and -)
    npwp_match = re.search(r'\d[\d.\-]{10,}\d', query_text)
    if npwp_match:
        raw_npwp = npwp_match.group(0)
        clean = re.sub(r'[.\-]', '', raw_npwp)
        intent = "NPWP_SEARCH"
        entities = _search_by_npwp(db, clean, body.limit)
    else:
        # Extract the search term: strip common Indonesian filler words
        clean_q = _clean_query(query_text)
        entities = _search_by_name(db, clean_q, body.limit)

    found = len(entities) > 0
    if found:
        if len(entities) == 1:
            msg = f"✅ Ditemukan: **{entities[0].name}**"
            if entities[0].npwp:
                msg += f" (NPWP: {entities[0].npwp})"
            msg += f". Jenis: {entities[0].entity_type}."
        else:
            names = ", ".join(e.name for e in entities[:3])
            msg = f"✅ Ditemukan {len(entities)} entitas yang cocok: {names}{'...' if len(entities)>3 else ''}."
    else:
        msg = f"❌ Tidak ditemukan entitas yang cocok dengan \"{query_text}\" di database SmartWeb."

    return AssistantResponse(
        query=query_text,
        intent=intent,
        found=found,
        match_count=len(entities),
        entities=entities,
        message=msg,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Internal search helpers
# ---------------------------------------------------------------------------

def _search_by_npwp(db: Session, clean_npwp: str, limit: int) -> List[MatchedEntity]:
    results: List[MatchedEntity] = []
    tps = (
        db.query(Taxpayer)
        .filter(Taxpayer.npwp_masked.ilike(f"%{clean_npwp}%"))
        .limit(limit)
        .all()
    )
    for tp in tps:
        results.append(
            MatchedEntity(
                entity_type="TAXPAYER",
                id=tp.id,
                name=tp.name,
                npwp=tp.npwp_masked,
                entity_subtype=tp.entity_type,
                status=tp.status,
                graph_url=f"/network-explorer?npwp={tp.npwp_masked or ''}",
                confidence=0.98,
            )
        )
    return results


def _search_by_name(db: Session, q: str, limit: int) -> List[MatchedEntity]:
    if len(q) < 2:
        return []

    pattern = f"%{q}%"
    results: List[MatchedEntity] = []

    # Taxpayers
    sim = func.similarity(Taxpayer.name, q)
    tps = (
        db.query(Taxpayer)
        .filter(or_(Taxpayer.name.ilike(pattern), sim > 0.2))
        .order_by(sim.desc())
        .limit(limit)
        .all()
    )
    for tp in tps:
        results.append(
            MatchedEntity(
                entity_type="TAXPAYER",
                id=tp.id,
                name=tp.name,
                npwp=tp.npwp_masked,
                entity_subtype=tp.entity_type,
                status=tp.status,
                graph_url=f"/network-explorer?npwp={tp.npwp_masked or ''}",
                confidence=0.85,
            )
        )

    # Beneficial Owners
    sim_bo = func.similarity(BeneficialOwner.name, q)
    bos = (
        db.query(BeneficialOwner)
        .filter(or_(BeneficialOwner.name.ilike(pattern), sim_bo > 0.2))
        .order_by(sim_bo.desc())
        .limit(limit)
        .all()
    )
    for bo in bos:
        results.append(
            MatchedEntity(
                entity_type="BENEFICIAL_OWNER",
                id=bo.id,
                name=bo.name,
                nationality=bo.nationality,
                confidence=0.80,
            )
        )

    # Groups
    sim_g = func.similarity(Group.name, q)
    groups = (
        db.query(Group)
        .filter(or_(Group.name.ilike(pattern), sim_g > 0.2))
        .order_by(sim_g.desc())
        .limit(limit)
        .all()
    )
    for g in groups:
        results.append(
            MatchedEntity(
                entity_type="GROUP",
                id=g.id,
                name=g.name,
                confidence=0.75,
            )
        )

    # Officers
    sim_o = func.similarity(Officer.name, q)
    officers = (
        db.query(Officer)
        .filter(or_(Officer.name.ilike(pattern), sim_o > 0.2))
        .order_by(sim_o.desc())
        .limit(3)
        .all()
    )
    for o in officers:
        results.append(
            MatchedEntity(
                entity_type="OFFICER",
                id=o.id,
                name=o.name,
                entity_subtype=o.position,
                confidence=0.70,
            )
        )

    results.sort(key=lambda x: x.confidence, reverse=True)
    return results[:limit]


def _clean_query(q: str) -> str:
    """Strip Indonesian filler words for cleaner name search."""
    stopwords = [
        "apakah", "cari", "temukan", "ada", "di", "database", "untuk",
        "tampilkan", "link", "graph", "entitas", "wajib pajak", "dengan",
        "nama", "mirip", "yang", "adalah", "sudah",
    ]
    result = q.lower()
    for word in stopwords:
        result = result.replace(word, " ")
    return re.sub(r'\s+', ' ', result).strip()
