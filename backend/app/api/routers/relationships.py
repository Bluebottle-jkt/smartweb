"""
Relationships router – query, filter, and inspect entity relationships.

Endpoints:
  GET  /relationships            – paginated list with optional filters
  GET  /relationships/{id}       – single relationship detail
  GET  /relationships/entity/{type}/{id}  – all rels for a given entity
  GET  /relationships/ownership-chain/{taxpayer_id}  – ownership path summary
"""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.db.models.relationship import Relationship, RelationshipType, EntityType
from app.db.models import Taxpayer, BeneficialOwner, Officer

router = APIRouter(prefix="/relationships", tags=["relationships"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_entity_name(db: Session, etype: str, eid: int) -> str:
    """Return display name for any entity type."""
    try:
        if etype == "TAXPAYER":
            obj = db.query(Taxpayer).filter(Taxpayer.id == eid).first()
            return obj.name if obj else f"WP#{eid}"
        if etype == "BENEFICIAL_OWNER":
            obj = db.query(BeneficialOwner).filter(BeneficialOwner.id == eid).first()
            return obj.name if obj else f"BO#{eid}"
        if etype == "OFFICER":
            obj = db.query(Officer).filter(Officer.id == eid).first()
            return obj.name if obj else f"Officer#{eid}"
    except Exception:
        pass
    return f"{etype}#{eid}"


def _rel_to_dict(rel: Relationship, db: Session) -> dict:
    return {
        "id": rel.id,
        "from_entity_type": rel.from_entity_type,
        "from_entity_id": rel.from_entity_id,
        "from_entity_name": _resolve_entity_name(db, rel.from_entity_type, rel.from_entity_id),
        "to_entity_type": rel.to_entity_type,
        "to_entity_id": rel.to_entity_id,
        "to_entity_name": _resolve_entity_name(db, rel.to_entity_type, rel.to_entity_id),
        "relationship_type": rel.relationship_type,
        "pct": float(rel.pct) if rel.pct is not None else None,
        "effective_from": rel.effective_from.isoformat() if rel.effective_from else None,
        "effective_to": rel.effective_to.isoformat() if rel.effective_to else None,
        "confidence": float(rel.confidence) if rel.confidence is not None else None,
        "source": rel.source,
        "notes": rel.notes,
    }


# ---------------------------------------------------------------------------
# GET /relationships
# ---------------------------------------------------------------------------

@router.get("")
def list_relationships(
    relationship_type: Optional[str] = Query(None),
    from_entity_type: Optional[str] = Query(None),
    to_entity_type: Optional[str] = Query(None),
    min_pct: Optional[float] = Query(None, ge=0, le=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Paginated list of relationships with optional filters."""
    q = db.query(Relationship)

    if relationship_type:
        q = q.filter(Relationship.relationship_type == relationship_type)
    if from_entity_type:
        q = q.filter(Relationship.from_entity_type == from_entity_type)
    if to_entity_type:
        q = q.filter(Relationship.to_entity_type == to_entity_type)
    if min_pct is not None:
        q = q.filter(Relationship.pct >= min_pct)

    total = q.count()
    rels = q.order_by(Relationship.id.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "results": [_rel_to_dict(r, db) for r in rels],
    }


# ---------------------------------------------------------------------------
# GET /relationships/entity/{entity_type}/{entity_id}
# ---------------------------------------------------------------------------

@router.get("/entity/{entity_type}/{entity_id}")
def relationships_for_entity(
    entity_type: str,
    entity_id: int,
    direction: Optional[str] = Query("both", regex="^(from|to|both)$"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """All relationships for a given entity, with optional direction filter."""
    q = db.query(Relationship)

    if direction == "from":
        q = q.filter(
            Relationship.from_entity_type == entity_type,
            Relationship.from_entity_id == entity_id,
        )
    elif direction == "to":
        q = q.filter(
            Relationship.to_entity_type == entity_type,
            Relationship.to_entity_id == entity_id,
        )
    else:
        q = q.filter(
            or_(
                (Relationship.from_entity_type == entity_type) & (Relationship.from_entity_id == entity_id),
                (Relationship.to_entity_type == entity_type) & (Relationship.to_entity_id == entity_id),
            )
        )

    rels = q.order_by(Relationship.relationship_type, Relationship.pct.desc().nullslast()).limit(500).all()

    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "count": len(rels),
        "relationships": [_rel_to_dict(r, db) for r in rels],
    }


# ---------------------------------------------------------------------------
# GET /relationships/ownership-chain/{taxpayer_id}
# ---------------------------------------------------------------------------

@router.get("/ownership-chain/{taxpayer_id}")
def ownership_chain(
    taxpayer_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return direct ownership layer for a taxpayer:
    - Shareholders (who owns this WP)
    - Subsidiaries (entities this WP owns)
    - Beneficial owners
    """
    # Shareholders: someone → TAXPAYER
    shareholders_rels = (
        db.query(Relationship)
        .filter(
            Relationship.to_entity_type == "TAXPAYER",
            Relationship.to_entity_id == taxpayer_id,
            Relationship.relationship_type == "OWNERSHIP",
        )
        .order_by(Relationship.pct.desc().nullslast())
        .all()
    )

    # Subsidiaries: TAXPAYER → something
    subsidiary_rels = (
        db.query(Relationship)
        .filter(
            Relationship.from_entity_type == "TAXPAYER",
            Relationship.from_entity_id == taxpayer_id,
            Relationship.relationship_type == "OWNERSHIP",
        )
        .order_by(Relationship.pct.desc().nullslast())
        .all()
    )

    # BO links
    bo_rels = (
        db.query(Relationship)
        .filter(
            or_(
                (Relationship.from_entity_type == "TAXPAYER") & (Relationship.from_entity_id == taxpayer_id),
                (Relationship.to_entity_type == "TAXPAYER") & (Relationship.to_entity_id == taxpayer_id),
            ),
            Relationship.relationship_type != "OWNERSHIP",
        )
        .all()
    )

    taxpayer = db.query(Taxpayer).filter(Taxpayer.id == taxpayer_id).first()
    if not taxpayer:
        raise HTTPException(status_code=404, detail="Taxpayer not found")

    return {
        "taxpayer_id": taxpayer_id,
        "taxpayer_name": taxpayer.name,
        "npwp": taxpayer.npwp_masked,
        "shareholders": [_rel_to_dict(r, db) for r in shareholders_rels],
        "subsidiaries": [_rel_to_dict(r, db) for r in subsidiary_rels],
        "other_relationships": [_rel_to_dict(r, db) for r in bo_rels],
        "total_pct_owned": sum(
            float(r.pct) for r in shareholders_rels if r.pct is not None
        ),
    }


# ---------------------------------------------------------------------------
# GET /relationships/{id}
# ---------------------------------------------------------------------------

@router.get("/{rel_id}")
def get_relationship(
    rel_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rel = db.query(Relationship).filter(Relationship.id == rel_id).first()
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return _rel_to_dict(rel, db)
