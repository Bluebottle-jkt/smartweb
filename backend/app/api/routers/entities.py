"""
Entity discovery / autocomplete router.

Provides richer suggestions than /search/suggest by including:
- NPWP
- entity subtype
- city (extracted from address field)
- KPP / Kanwil (if the geography tables are seeded)

Used by EntityAutocompleteInput and the chat assistant.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import case, func, literal_column, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import BeneficialOwner, Group, Officer, Taxpayer
from app.db.session import get_db

router = APIRouter(prefix="/entities", tags=["entities"])


class EntitySuggestionItem(BaseModel):
    entity_type: str
    id: int
    name: str
    npwp_masked: Optional[str] = None
    subtitle: Optional[str] = None
    entity_subtype: Optional[str] = None
    city: Optional[str] = None
    rank: float = 0.0


@router.get("/suggest", response_model=List[EntitySuggestionItem])
def entity_suggest(
    q: str = Query(..., min_length=1, description="Name or NPWP partial search"),
    limit: int = Query(8, ge=1, le=30),
    entity_types: Optional[str] = Query(
        None,
        description="Comma-separated filter: TAXPAYER,BENEFICIAL_OWNER,GROUP,OFFICER",
    ),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Richer entity autocomplete supporting:
    - partial name search (pg_trgm)
    - partial NPWP search (ILIKE)
    - entity-type filter
    Returns results sorted by relevance rank.
    """
    types_filter: Optional[set] = None
    if entity_types:
        types_filter = {t.strip().upper() for t in entity_types.split(",")}

    import re as _re
    query_pattern = f"%{q}%"
    # Build NPWP ILIKE pattern that bridges masked chars like '17.***.***.*-***.100'
    _digit_groups = _re.findall(r'\d+', q)
    if len(_digit_groups) >= 2:
        npwp_pattern = f"%{_digit_groups[0]}%{_digit_groups[-1]}%"
    elif len(_digit_groups) == 1:
        npwp_pattern = f"%{_digit_groups[0]}%"
    else:
        npwp_pattern = f"%{q.replace('.', '').replace('-', '')}%"
    results: list[EntitySuggestionItem] = []

    # ---- Taxpayers --------------------------------------------------------
    if not types_filter or "TAXPAYER" in types_filter:
        sim = func.similarity(Taxpayer.name, q)
        rank_expr = case(
            (Taxpayer.npwp_masked.ilike(npwp_pattern), 5),
            (Taxpayer.name.ilike(f"{q}%"), 3),
            (Taxpayer.name.ilike(query_pattern), 2),
            else_=sim,
        )
        rows = (
            db.query(
                Taxpayer.id,
                Taxpayer.name,
                Taxpayer.npwp_masked,
                Taxpayer.entity_type,
                Taxpayer.address,
                rank_expr.label("rank"),
            )
            .filter(
                or_(
                    Taxpayer.name.ilike(query_pattern),
                    Taxpayer.npwp_masked.ilike(npwp_pattern),
                    sim > 0.15,
                )
            )
            .order_by(rank_expr.desc())
            .limit(limit)
            .all()
        )
        for r in rows:
            city = _extract_city(r.address)
            results.append(
                EntitySuggestionItem(
                    entity_type="TAXPAYER",
                    id=r.id,
                    name=r.name,
                    npwp_masked=r.npwp_masked,
                    subtitle=r.npwp_masked,
                    entity_subtype=r.entity_type,
                    city=city,
                    rank=float(r.rank or 0),
                )
            )

    # ---- Beneficial Owners ------------------------------------------------
    if not types_filter or "BENEFICIAL_OWNER" in types_filter:
        sim = func.similarity(BeneficialOwner.name, q)
        rank_expr = case(
            (BeneficialOwner.name.ilike(f"{q}%"), 3),
            (BeneficialOwner.name.ilike(query_pattern), 2),
            else_=sim,
        )
        rows = (
            db.query(
                BeneficialOwner.id,
                BeneficialOwner.name,
                BeneficialOwner.nationality,
                rank_expr.label("rank"),
            )
            .filter(
                or_(
                    BeneficialOwner.name.ilike(query_pattern),
                    sim > 0.15,
                )
            )
            .order_by(rank_expr.desc())
            .limit(limit)
            .all()
        )
        for r in rows:
            results.append(
                EntitySuggestionItem(
                    entity_type="BENEFICIAL_OWNER",
                    id=r.id,
                    name=r.name,
                    subtitle=r.nationality or "Beneficial Owner",
                    rank=float(r.rank or 0),
                )
            )

    # ---- Groups -----------------------------------------------------------
    if not types_filter or "GROUP" in types_filter:
        sim = func.similarity(Group.name, q)
        rank_expr = case(
            (Group.name.ilike(f"{q}%"), 3),
            (Group.name.ilike(query_pattern), 2),
            else_=sim,
        )
        rows = (
            db.query(Group.id, Group.name, Group.sector, rank_expr.label("rank"))
            .filter(or_(Group.name.ilike(query_pattern), sim > 0.15))
            .order_by(rank_expr.desc())
            .limit(limit)
            .all()
        )
        for r in rows:
            results.append(
                EntitySuggestionItem(
                    entity_type="GROUP",
                    id=r.id,
                    name=r.name,
                    subtitle=r.sector or "Grup WP",
                    rank=float(r.rank or 0),
                )
            )

    # ---- Officers ---------------------------------------------------------
    if not types_filter or "OFFICER" in types_filter:
        sim = func.similarity(Officer.name, q)
        rank_expr = case(
            (Officer.name.ilike(f"{q}%"), 3),
            (Officer.name.ilike(query_pattern), 2),
            else_=sim,
        )
        rows = (
            db.query(Officer.id, Officer.name, Officer.position, rank_expr.label("rank"))
            .filter(or_(Officer.name.ilike(query_pattern), sim > 0.15))
            .order_by(rank_expr.desc())
            .limit(limit)
            .all()
        )
        for r in rows:
            results.append(
                EntitySuggestionItem(
                    entity_type="OFFICER",
                    id=r.id,
                    name=r.name,
                    entity_subtype=r.position,
                    rank=float(r.rank or 0),
                )
            )

    # Sort combined results by rank
    results.sort(key=lambda x: x.rank, reverse=True)
    return results[:limit]


@router.get("/{entity_type}/{entity_id}/graph-link")
def entity_graph_link(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return the direct frontend URL to open a graph for this entity."""
    entity_type = entity_type.upper()
    if entity_type == "TAXPAYER":
        tp = db.query(Taxpayer).filter(Taxpayer.id == entity_id).first()
        if not tp:
            return {"error": "Not found"}
        npwp = tp.npwp_masked or ""
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "name": tp.name,
            "npwp": npwp,
            "graph_url": f"/network-explorer?npwp={npwp}",
        }
    return {"graph_url": f"/network-explorer?entity_type={entity_type}&entity_id={entity_id}"}


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _extract_city(address: Optional[str]) -> Optional[str]:
    """Best-effort city extraction from the free-text address field."""
    if not address:
        return None
    lines = [ln.strip() for ln in address.splitlines() if ln.strip()]
    if not lines:
        return None
    last = lines[-1]
    if "," in last:
        return last.split(",")[0].strip()[:50]
    return last[:50]
