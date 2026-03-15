from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.db.models import BeneficialOwner, EntityType, Relationship, Taxpayer, Officer, Address, Intermediary


@dataclass(frozen=True)
class NodeKey:
    entity_type: EntityType
    entity_id: int


def build_network_graph(
    db: Session,
    root_type: EntityType,
    root_id: int,
    year: int,
    depth: int,
    max_nodes: int
) -> Dict[str, object]:
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    layer_by_node: Dict[NodeKey, int] = {NodeKey(root_type, root_id): 0}
    frontier: List[NodeKey] = [NodeKey(root_type, root_id)]
    edges: Dict[int, Relationship] = {}
    truncated = False

    for hop in range(1, depth + 1):
        if not frontier:
            break

        relationships = _fetch_relationships_for_frontier(db, frontier, year_start, year_end)
        next_frontier: List[NodeKey] = []

        for rel in relationships:
            if rel.id in edges:
                continue

            source = NodeKey(rel.from_entity_type, rel.from_entity_id)
            target = NodeKey(rel.to_entity_type, rel.to_entity_id)

            for node in (source, target):
                if node not in layer_by_node:
                    if len(layer_by_node) >= max_nodes:
                        truncated = True
                        continue
                    layer_by_node[node] = hop
                    next_frontier.append(node)

            if source in layer_by_node and target in layer_by_node:
                edges[rel.id] = rel

        frontier = next_frontier
        if truncated:
            break

    nodes_payload = _build_nodes_payload(db, layer_by_node)
    edges_payload = _build_edges_payload(edges, layer_by_node)
    layer_counts = _count_layers(layer_by_node)

    return {
        "nodes": nodes_payload,
        "edges": edges_payload,
        "layer_counts": layer_counts,
        "truncated": truncated,
    }


def build_network_layer_stats(
    db: Session,
    root_type: EntityType,
    root_id: int,
    year: int,
    depth: int,
    max_nodes: int
) -> Dict[str, object]:
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    layer_by_node: Dict[NodeKey, int] = {NodeKey(root_type, root_id): 0}
    frontier: List[NodeKey] = [NodeKey(root_type, root_id)]
    truncated = False

    for hop in range(1, depth + 1):
        if not frontier:
            break

        relationships = _fetch_relationships_for_frontier(db, frontier, year_start, year_end)
        next_frontier: List[NodeKey] = []

        for rel in relationships:
            source = NodeKey(rel.from_entity_type, rel.from_entity_id)
            target = NodeKey(rel.to_entity_type, rel.to_entity_id)

            for node in (source, target):
                if node not in layer_by_node:
                    if len(layer_by_node) >= max_nodes:
                        truncated = True
                        continue
                    layer_by_node[node] = hop
                    next_frontier.append(node)

        frontier = next_frontier
        if truncated:
            break

    return {
        "layer_counts": _count_layers(layer_by_node),
        "truncated": truncated,
    }


def _fetch_relationships_for_frontier(
    db: Session,
    frontier: Iterable[NodeKey],
    year_start: date,
    year_end: date
) -> List[Relationship]:
    type_to_ids: Dict[EntityType, Set[int]] = {}
    for node in frontier:
        type_to_ids.setdefault(node.entity_type, set()).add(node.entity_id)

    if not type_to_ids:
        return []

    filters = []
    for entity_type, ids in type_to_ids.items():
        ids_list = list(ids)
        filters.append(and_(Relationship.from_entity_type == entity_type, Relationship.from_entity_id.in_(ids_list)))
        filters.append(and_(Relationship.to_entity_type == entity_type, Relationship.to_entity_id.in_(ids_list)))

    year_filter = and_(
        or_(Relationship.effective_from.is_(None), Relationship.effective_from <= year_end),
        or_(Relationship.effective_to.is_(None), Relationship.effective_to >= year_start)
    )

    return (
        db.query(Relationship)
        .filter(or_(*filters))
        .filter(year_filter)
        .all()
    )


def _build_nodes_payload(db: Session, layer_by_node: Dict[NodeKey, int]) -> List[dict]:
    # Collect IDs by entity type
    taxpayer_ids = [node.entity_id for node in layer_by_node if node.entity_type == EntityType.TAXPAYER]
    bo_ids = [node.entity_id for node in layer_by_node if node.entity_type == EntityType.BENEFICIAL_OWNER]
    officer_ids = [node.entity_id for node in layer_by_node if node.entity_type == EntityType.OFFICER]
    address_ids = [node.entity_id for node in layer_by_node if node.entity_type == EntityType.ADDRESS]
    intermediary_ids = [node.entity_id for node in layer_by_node if node.entity_type == EntityType.INTERMEDIARY]

    # Fetch entities from database
    taxpayers = db.query(Taxpayer).filter(Taxpayer.id.in_(taxpayer_ids)).all() if taxpayer_ids else []
    beneficial_owners = db.query(BeneficialOwner).filter(BeneficialOwner.id.in_(bo_ids)).all() if bo_ids else []
    officers = db.query(Officer).filter(Officer.id.in_(officer_ids)).all() if officer_ids else []
    addresses = db.query(Address).filter(Address.id.in_(address_ids)).all() if address_ids else []
    intermediaries = db.query(Intermediary).filter(Intermediary.id.in_(intermediary_ids)).all() if intermediary_ids else []

    # Build lookup maps
    taxpayer_map = {tp.id: tp for tp in taxpayers}
    bo_map = {bo.id: bo for bo in beneficial_owners}
    officer_map = {o.id: o for o in officers}
    address_map = {a.id: a for a in addresses}
    intermediary_map = {i.id: i for i in intermediaries}

    nodes_payload = []
    for node, layer in layer_by_node.items():
        node_id = _build_node_id(node.entity_type, node.entity_id)

        npwp: Optional[str] = None

        if node.entity_type == EntityType.TAXPAYER:
            tp = taxpayer_map.get(node.entity_id)
            name = tp.name if tp else f"Taxpayer {node.entity_id}"
            location = _format_location_from_address(tp.address if tp else None, "Indonesia")
            entity_subtype = tp.entity_type if tp else None
            npwp = tp.npwp_masked if tp else None
            category = "Entity"

        elif node.entity_type == EntityType.BENEFICIAL_OWNER:
            bo = bo_map.get(node.entity_id)
            name = bo.name if bo else f"Beneficial Owner {node.entity_id}"
            location = _format_location_from_country(bo.nationality if bo else None)
            entity_subtype = None
            category = "Officer"  # BOs are shown as Officer category in ICIJ-style

        elif node.entity_type == EntityType.OFFICER:
            officer = officer_map.get(node.entity_id)
            name = officer.name if officer else f"Officer {node.entity_id}"
            location = _format_location_from_country(officer.nationality if officer else None)
            entity_subtype = officer.position if officer else None
            category = "Officer"

        elif node.entity_type == EntityType.ADDRESS:
            addr = address_map.get(node.entity_id)
            name = f"{addr.city}, {addr.province}" if addr else f"Address {node.entity_id}"
            location = f"{addr.city}, {addr.province}, {addr.country}" if addr else "Indonesia"
            entity_subtype = addr.address_type if addr else None
            category = "Address"

        elif node.entity_type == EntityType.INTERMEDIARY:
            interm = intermediary_map.get(node.entity_id)
            name = interm.name if interm else f"Intermediary {node.entity_id}"
            location = _format_location_from_country(interm.country if interm else None)
            entity_subtype = interm.intermediary_type if interm else None
            category = "Intermediary"

        else:
            name = f"Entity {node.entity_id}"
            location = _format_location_from_country(None)
            entity_subtype = None
            category = "Entity"

        nodes_payload.append({
            "id": node_id,
            "entity_id": node.entity_id,
            "entity_type": node.entity_type.value,
            "entity_subtype": entity_subtype,
            "name": name,
            "npwp": npwp,
            "location_label": location,
            "layer": layer,
            "category": category,
        })

    return nodes_payload


def _build_edges_payload(
    edges: Dict[int, Relationship],
    layer_by_node: Dict[NodeKey, int]
) -> List[dict]:
    edges_payload = []

    for rel_id, rel in edges.items():
        source = NodeKey(rel.from_entity_type, rel.from_entity_id)
        target = NodeKey(rel.to_entity_type, rel.to_entity_id)
        if source not in layer_by_node or target not in layer_by_node:
            continue

        layer = max(layer_by_node[source], layer_by_node[target])
        label = rel.relationship_type.value
        pct_label = _format_pct(rel.pct)
        if pct_label:
            label = f"{label} {pct_label}"

        edges_payload.append({
            "id": f"rel-{rel_id}",
            "source": _build_node_id(source.entity_type, source.entity_id),
            "target": _build_node_id(target.entity_type, target.entity_id),
            "relationship_type": rel.relationship_type.value,
            "label": label,
            "layer": layer,
            "pct": float(rel.pct) if rel.pct is not None else None,
            "confidence": float(rel.confidence) if rel.confidence is not None else None,
            "notes": rel.notes,
            "source_ref": rel.source,
            "effective_from": rel.effective_from.isoformat() if rel.effective_from else None,
            "effective_to": rel.effective_to.isoformat() if rel.effective_to else None,
        })

    return edges_payload


def _count_layers(layer_by_node: Dict[NodeKey, int]) -> Dict[int, int]:
    counts: Dict[int, int] = {}
    for layer in layer_by_node.values():
        counts[layer] = counts.get(layer, 0) + 1
    return counts


def _build_node_id(entity_type: EntityType, entity_id: int) -> str:
    return f"{entity_type.value}:{entity_id}"


def _format_location_from_address(address: Optional[str], country: str) -> str:
    city = "Tidak diketahui"
    province = "Tidak diketahui"

    if address:
        lines = [line.strip() for line in address.splitlines() if line.strip()]
        if lines:
            last_line = lines[-1]
            if "," in last_line:
                city_part, rest = last_line.split(",", 1)
                city = city_part.strip() or city
                rest = rest.strip()
                if rest:
                    province = rest.split()[0].strip() or province
            else:
                city = last_line.strip() or city

    return f"{city}, {province}, {country}"


def _format_location_from_country(country: Optional[str]) -> str:
    country_name = country or "Indonesia"
    return f"Tidak diketahui, Tidak diketahui, {country_name}"


def _format_pct(value: Optional[Decimal]) -> Optional[str]:
    if value is None:
        return None
    pct = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return f"{pct}%"
