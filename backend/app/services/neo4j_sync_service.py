"""
Neo4j Sync Service
==================

Synchronises the PostgreSQL relational graph into Neo4j for accelerated
graph queries.  Designed to be:
- idempotent (MERGE, not CREATE)
- incremental (can sync a single entity or the whole dataset)
- safe to call even when Neo4j is unavailable (returns graceful error)

Node labels used: Taxpayer, BeneficialOwner, Officer, Address, Intermediary
Relationship types mirror the RelationshipType enum: OWNERSHIP, CONTROL, FAMILY, AFFILIATION_OTHER
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.neo4j import is_neo4j_available, run_write
from app.db.models import (
    Address,
    BeneficialOwner,
    EntityType,
    GraphSyncState,
    Intermediary,
    Officer,
    Relationship,
    Taxpayer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bootstrap: sync all entities and relationships
# ---------------------------------------------------------------------------

def sync_all(db: Session) -> Dict[str, Any]:
    """Full one-shot synchronisation from PostgreSQL → Neo4j."""
    if not is_neo4j_available():
        return {"success": False, "reason": "Neo4j is not available"}

    stats: Dict[str, int] = {
        "taxpayers": 0, "beneficial_owners": 0, "officers": 0,
        "addresses": 0, "intermediaries": 0, "relationships": 0,
    }

    # Sync nodes
    for tp in db.query(Taxpayer).all():
        _upsert_taxpayer(tp)
        _mark_synced(db, "TAXPAYER", tp.id)
        stats["taxpayers"] += 1

    for bo in db.query(BeneficialOwner).all():
        _upsert_beneficial_owner(bo)
        _mark_synced(db, "BENEFICIAL_OWNER", bo.id)
        stats["beneficial_owners"] += 1

    for o in db.query(Officer).all():
        _upsert_officer(o)
        _mark_synced(db, "OFFICER", o.id)
        stats["officers"] += 1

    for a in db.query(Address).all():
        _upsert_address(a)
        _mark_synced(db, "ADDRESS", a.id)
        stats["addresses"] += 1

    for i in db.query(Intermediary).all():
        _upsert_intermediary(i)
        _mark_synced(db, "INTERMEDIARY", i.id)
        stats["intermediaries"] += 1

    # Sync relationships
    for rel in db.query(Relationship).all():
        _upsert_relationship(rel)
        stats["relationships"] += 1

    db.commit()
    logger.info("Neo4j full sync completed: %s", stats)
    return {"success": True, "stats": stats}


# ---------------------------------------------------------------------------
# Incremental: sync a single entity and its relationships
# ---------------------------------------------------------------------------

def sync_entity(db: Session, entity_type: str, entity_id: int) -> Dict[str, Any]:
    """Sync a single entity and all relationships touching it."""
    if not is_neo4j_available():
        return {"success": False, "reason": "Neo4j is not available"}

    try:
        _sync_node(db, entity_type, entity_id)
        _sync_entity_relationships(db, entity_type, entity_id)
        _mark_synced(db, entity_type, entity_id)
        db.commit()
        return {"success": True, "entity_type": entity_type, "entity_id": entity_id}
    except Exception as exc:
        _mark_sync_error(db, entity_type, entity_id, str(exc))
        db.commit()
        return {"success": False, "reason": str(exc)}


# ---------------------------------------------------------------------------
# Neo4j MERGE helpers
# ---------------------------------------------------------------------------

def _upsert_taxpayer(tp: Taxpayer) -> None:
    run_write(
        """
        MERGE (n:Taxpayer {entity_id: $id})
        SET n.npwp = $npwp,
            n.name = $name,
            n.entity_type = $etype,
            n.status = $status,
            n.synced_at = $now
        """,
        {
            "id": tp.id,
            "npwp": tp.npwp_masked or "",
            "name": tp.name or "",
            "etype": tp.entity_type or "",
            "status": tp.status or "",
            "now": _now_iso(),
        },
    )


def _upsert_beneficial_owner(bo: BeneficialOwner) -> None:
    run_write(
        """
        MERGE (n:BeneficialOwner {entity_id: $id})
        SET n.name = $name,
            n.nationality = $nationality,
            n.synced_at = $now
        """,
        {"id": bo.id, "name": bo.name or "", "nationality": bo.nationality or "", "now": _now_iso()},
    )


def _upsert_officer(o: Officer) -> None:
    run_write(
        """
        MERGE (n:Officer {entity_id: $id})
        SET n.name = $name,
            n.position = $position,
            n.nationality = $nationality,
            n.synced_at = $now
        """,
        {
            "id": o.id, "name": o.name or "", "position": o.position or "",
            "nationality": o.nationality or "", "now": _now_iso(),
        },
    )


def _upsert_address(a: Address) -> None:
    run_write(
        """
        MERGE (n:Address {entity_id: $id})
        SET n.city = $city,
            n.province = $province,
            n.country = $country,
            n.synced_at = $now
        """,
        {
            "id": a.id, "city": a.city or "", "province": a.province or "",
            "country": a.country or "Indonesia", "now": _now_iso(),
        },
    )


def _upsert_intermediary(i: Intermediary) -> None:
    run_write(
        """
        MERGE (n:Intermediary {entity_id: $id})
        SET n.name = $name,
            n.type = $type,
            n.country = $country,
            n.synced_at = $now
        """,
        {
            "id": i.id, "name": i.name or "",
            "type": i.intermediary_type or "", "country": i.country or "",
            "now": _now_iso(),
        },
    )


def _upsert_relationship(rel: Relationship) -> None:
    """
    Merge a directed relationship in Neo4j.  Node labels are derived from
    the entity_type stored in the relationship record.
    """
    from_label = _entity_label(rel.from_entity_type.value)
    to_label = _entity_label(rel.to_entity_type.value)
    rel_type = rel.relationship_type.value

    cypher = f"""
    MATCH (a:{from_label} {{entity_id: $from_id}})
    MATCH (b:{to_label} {{entity_id: $to_id}})
    MERGE (a)-[r:{rel_type} {{rel_id: $rel_id}}]->(b)
    SET r.pct = $pct,
        r.confidence = $confidence,
        r.source = $source,
        r.synced_at = $now
    """
    run_write(cypher, {
        "from_id": rel.from_entity_id,
        "to_id": rel.to_entity_id,
        "rel_id": rel.id,
        "pct": float(rel.pct) if rel.pct is not None else None,
        "confidence": float(rel.confidence) if rel.confidence is not None else None,
        "source": rel.source or "",
        "now": _now_iso(),
    })


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sync_node(db: Session, entity_type: str, entity_id: int) -> None:
    etype = EntityType(entity_type)
    if etype == EntityType.TAXPAYER:
        obj = db.query(Taxpayer).filter(Taxpayer.id == entity_id).first()
        if obj:
            _upsert_taxpayer(obj)
    elif etype == EntityType.BENEFICIAL_OWNER:
        obj = db.query(BeneficialOwner).filter(BeneficialOwner.id == entity_id).first()
        if obj:
            _upsert_beneficial_owner(obj)
    elif etype == EntityType.OFFICER:
        obj = db.query(Officer).filter(Officer.id == entity_id).first()
        if obj:
            _upsert_officer(obj)
    elif etype == EntityType.ADDRESS:
        obj = db.query(Address).filter(Address.id == entity_id).first()
        if obj:
            _upsert_address(obj)
    elif etype == EntityType.INTERMEDIARY:
        obj = db.query(Intermediary).filter(Intermediary.id == entity_id).first()
        if obj:
            _upsert_intermediary(obj)


def _sync_entity_relationships(db: Session, entity_type: str, entity_id: int) -> None:
    from sqlalchemy import or_, and_
    etype = EntityType(entity_type)
    rels = db.query(Relationship).filter(
        or_(
            and_(Relationship.from_entity_type == etype, Relationship.from_entity_id == entity_id),
            and_(Relationship.to_entity_type == etype, Relationship.to_entity_id == entity_id),
        )
    ).all()
    for rel in rels:
        try:
            _upsert_relationship(rel)
        except Exception as e:
            logger.debug("Skipping rel %d: %s", rel.id, e)


def _mark_synced(db: Session, entity_type: str, entity_id: int) -> None:
    state = (
        db.query(GraphSyncState)
        .filter(GraphSyncState.entity_type == entity_type, GraphSyncState.entity_id == entity_id)
        .first()
    )
    if state:
        state.last_synced_at = datetime.now(timezone.utc)
        state.sync_status = "OK"
        state.error_message = None
    else:
        db.add(GraphSyncState(
            entity_type=entity_type,
            entity_id=entity_id,
            last_synced_at=datetime.now(timezone.utc),
            sync_status="OK",
        ))


def _mark_sync_error(db: Session, entity_type: str, entity_id: int, error: str) -> None:
    state = (
        db.query(GraphSyncState)
        .filter(GraphSyncState.entity_type == entity_type, GraphSyncState.entity_id == entity_id)
        .first()
    )
    if state:
        state.sync_status = "ERROR"
        state.error_message = error[:500]
    else:
        db.add(GraphSyncState(
            entity_type=entity_type,
            entity_id=entity_id,
            sync_status="ERROR",
            error_message=error[:500],
        ))


def _entity_label(entity_type: str) -> str:
    mapping = {
        "TAXPAYER": "Taxpayer",
        "BENEFICIAL_OWNER": "BeneficialOwner",
        "OFFICER": "Officer",
        "ADDRESS": "Address",
        "INTERMEDIARY": "Intermediary",
    }
    return mapping.get(entity_type, "Entity")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
