"""
Graph Intelligence Service
==========================

Pure-Python graph analytics running against the PostgreSQL database.
All detectors are designed to degrade gracefully when the underlying data is
sparse.  Neo4j is used as an accelerator when available; the same logic runs
against the SQL graph when Neo4j is offline.

Detectors implemented
---------------------
1. ownership_pyramid          – recursive effective-ownership computation
2. circular_transaction       – directed-cycle detection in relationship graph
3. beneficial_owner_inference – infer probable beneficial owners
4. vat_carousel               – VAT carousel pattern heuristics
5. shell_company              – composite shell-company risk scoring
6. nominee_director           – nominee / proxy-director detection
7. ai_discovery               – surface hidden relationships and clusters
"""
from __future__ import annotations

import logging
import math
from collections import defaultdict, deque
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.db.models import (
    BeneficialOwner,
    BeneficialOwnerTaxpayer,
    EntityType,
    Officer,
    Relationship,
    RelationshipType,
    Taxpayer,
    TaxpayerYearlyAffiliateTx,
    TaxpayerYearlyFinancial,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _npwp_ilike(npwp: str):
    """Build an ILIKE filter that matches masked NPWPs like '17.***.***.*-***.100'.
    Uses digit groups to bridge over the masked segments."""
    import re
    groups = re.findall(r'\d+', npwp)
    if len(groups) >= 2:
        return Taxpayer.npwp_masked.ilike(f"%{groups[0]}%{groups[-1]}%")
    if len(groups) == 1:
        return Taxpayer.npwp_masked.ilike(f"%{groups[0]}%")
    clean = npwp.replace(".", "").replace("-", "")
    return Taxpayer.npwp_masked.ilike(f"%{clean}%")


def _resolve_taxpayer(db: Session, npwp: str) -> Optional[Taxpayer]:
    return db.query(Taxpayer).filter(_npwp_ilike(npwp)).first()


def _year_filter(year: int):
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    from sqlalchemy import and_, or_
    return and_(
        or_(Relationship.effective_from.is_(None), Relationship.effective_from <= year_end),
        or_(Relationship.effective_to.is_(None), Relationship.effective_to >= year_start),
    )


def _get_all_relationships(db: Session, year: int) -> List[Relationship]:
    return db.query(Relationship).filter(_year_filter(year)).all()


def _ownership_edges(rels: List[Relationship]) -> List[Tuple[str, str, float]]:
    """Return (from_key, to_key, pct) tuples for OWNERSHIP relationships."""
    edges = []
    for r in rels:
        if r.relationship_type == RelationshipType.OWNERSHIP:
            pct = float(r.pct or 0)
            src = f"{r.from_entity_type.value}:{r.from_entity_id}"
            dst = f"{r.to_entity_type.value}:{r.to_entity_id}"
            edges.append((src, dst, pct))
    return edges


def _node_label(db: Session, entity_type: EntityType, entity_id: int) -> str:
    if entity_type == EntityType.TAXPAYER:
        t = db.query(Taxpayer).filter(Taxpayer.id == entity_id).first()
        return t.name if t else f"TAXPAYER:{entity_id}"
    if entity_type == EntityType.BENEFICIAL_OWNER:
        b = db.query(BeneficialOwner).filter(BeneficialOwner.id == entity_id).first()
        return b.name if b else f"BO:{entity_id}"
    if entity_type == EntityType.OFFICER:
        o = db.query(Officer).filter(Officer.id == entity_id).first()
        return o.name if o else f"OFFICER:{entity_id}"
    return f"{entity_type.value}:{entity_id}"


# ---------------------------------------------------------------------------
# 1. Ownership Pyramid Detection
# ---------------------------------------------------------------------------

def detect_ownership_pyramid(
    db: Session,
    root_npwp: str,
    year: int,
    max_depth: int = 5,
) -> Dict[str, Any]:
    """
    Recursively traverse OWNERSHIP relationships downward from the root entity
    and compute effective ownership at each downstream node.

    Effective ownership formula (chain product):
        root → A (70%) → B (80%) → C → effective_of_C = 70% × 80% = 56%
    """
    # Resolve root taxpayer
    taxpayer = _resolve_taxpayer(db, root_npwp)
    if not taxpayer:
        return {"error": f"Taxpayer with NPWP {root_npwp!r} not found"}

    rels = _get_all_relationships(db, year)
    # Build adjacency: from_key -> [(to_key, pct)]
    adj: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for src, dst, pct in _ownership_edges(rels):
        adj[src].append((dst, pct))

    root_key = f"TAXPAYER:{taxpayer.id}"
    # BFS with effective-ownership tracking
    effective: Dict[str, float] = {root_key: 100.0}
    chain: Dict[str, List[str]] = {root_key: [root_key]}
    visited: Set[str] = {root_key}
    queue: deque = deque([(root_key, 0)])
    pyramid_nodes = []

    while queue:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for neighbor, pct in adj.get(current, []):
            eff = effective[current] * (pct / 100.0)
            if neighbor not in visited:
                visited.add(neighbor)
                effective[neighbor] = eff
                chain[neighbor] = chain[current] + [neighbor]
                queue.append((neighbor, depth + 1))
            elif eff > effective.get(neighbor, 0):
                effective[neighbor] = eff
            pyramid_nodes.append({
                "node": neighbor,
                "effective_ownership_pct": round(eff, 4),
                "direct_pct": pct,
                "depth": depth + 1,
                "chain": chain[current] + [neighbor],
            })

    # Detect concentration: nodes where effective ownership > 25%
    controlled = [n for n in pyramid_nodes if n["effective_ownership_pct"] >= 25]
    risk_score = min(1.0, len(controlled) / max(1, 10)) + (0.3 if len(pyramid_nodes) > 5 else 0)

    return {
        "detection_type": "OWNERSHIP_PYRAMID",
        "root_npwp": root_npwp,
        "root_entity_id": taxpayer.id,
        "tax_year": year,
        "pyramid_nodes": pyramid_nodes,
        "controlled_entities_count": len(controlled),
        "max_chain_depth": max((n["depth"] for n in pyramid_nodes), default=0),
        "risk_score": round(min(1.0, risk_score), 3),
        "risk_level": _score_to_level(risk_score),
        "summary": (
            f"Found {len(pyramid_nodes)} downstream entities reachable via OWNERSHIP from "
            f"{taxpayer.name} ({root_npwp}). {len(controlled)} entities are >25% effectively owned."
        ),
        "evidence": {"nodes": pyramid_nodes[:50]},
    }


# ---------------------------------------------------------------------------
# 2. Circular Transaction Detection
# ---------------------------------------------------------------------------

def detect_circular_transactions(
    db: Session,
    root_npwp: str,
    year: int,
    max_depth: int = 5,
) -> Dict[str, Any]:
    """
    Detect directed cycles in the relationship graph starting from the root
    entity using DFS cycle detection (Johnson's SCC-style simplified).
    """
    taxpayer = _resolve_taxpayer(db, root_npwp)
    if not taxpayer:
        return {"error": f"Taxpayer with NPWP {root_npwp!r} not found"}

    rels = _get_all_relationships(db, year)
    # Build directed adjacency for ALL relationship types
    adj: Dict[str, Set[str]] = defaultdict(set)
    for r in rels:
        src = f"{r.from_entity_type.value}:{r.from_entity_id}"
        dst = f"{r.to_entity_type.value}:{r.to_entity_id}"
        adj[src].add(dst)

    root_key = f"TAXPAYER:{taxpayer.id}"
    cycles: List[List[str]] = []
    _dfs_find_cycles(root_key, adj, max_depth, [], set(), cycles)

    # Deduplicate cycles (canonicalise by rotating to smallest element)
    unique_cycles = _deduplicate_cycles(cycles)

    risk_score = min(1.0, len(unique_cycles) * 0.25)
    return {
        "detection_type": "CIRCULAR_TRANSACTION",
        "root_npwp": root_npwp,
        "root_entity_id": taxpayer.id,
        "tax_year": year,
        "cycles_found": len(unique_cycles),
        "cycles": unique_cycles[:20],
        "risk_score": round(risk_score, 3),
        "risk_level": _score_to_level(risk_score),
        "summary": (
            f"Detected {len(unique_cycles)} directed relationship cycle(s) starting from "
            f"{taxpayer.name} ({root_npwp}) within depth {max_depth}."
        ),
        "reason_codes": ["CIRCULAR_OWNERSHIP"] if unique_cycles else [],
        "evidence": {"cycles": unique_cycles[:10]},
    }


def _dfs_find_cycles(
    node: str,
    adj: Dict[str, Set[str]],
    max_depth: int,
    path: List[str],
    path_set: Set[str],
    cycles: List[List[str]],
) -> None:
    if len(path) > max_depth:
        return
    path_set.add(node)
    path.append(node)
    for neighbor in adj.get(node, set()):
        if neighbor == path[0] and len(path) > 1:
            cycles.append(list(path))
        elif neighbor not in path_set:
            _dfs_find_cycles(neighbor, adj, max_depth, path, path_set, cycles)
    path.pop()
    path_set.discard(node)


def _deduplicate_cycles(cycles: List[List[str]]) -> List[List[str]]:
    seen = set()
    result = []
    for c in cycles:
        if not c:
            continue
        min_idx = c.index(min(c))
        canonical = tuple(c[min_idx:] + c[:min_idx])
        if canonical not in seen:
            seen.add(canonical)
            result.append(list(canonical))
    return result


# ---------------------------------------------------------------------------
# 3. Beneficial Owner Inference
# ---------------------------------------------------------------------------

def infer_beneficial_owners(
    db: Session,
    root_npwp: str,
    year: int,
    min_confidence: float = 0.4,
) -> Dict[str, Any]:
    """
    Infer probable beneficial owners for a taxpayer using:
    - Direct BO links
    - Indirect ownership chains
    - Shared officer / director patterns
    """
    taxpayer = _resolve_taxpayer(db, root_npwp)
    if not taxpayer:
        return {"error": f"Taxpayer with NPWP {root_npwp!r} not found"}

    candidates = []

    # --- Signal A: Direct BO registration ---
    direct_bos = (
        db.query(BeneficialOwnerTaxpayer, BeneficialOwner)
        .join(BeneficialOwner)
        .filter(BeneficialOwnerTaxpayer.taxpayer_id == taxpayer.id)
        .all()
    )
    for link, bo in direct_bos:
        candidates.append({
            "entity_type": "BENEFICIAL_OWNER",
            "entity_id": bo.id,
            "name": bo.name,
            "nationality": bo.nationality,
            "inferred": False,
            "confidence": 0.95,
            "evidence": [f"Direct BO registration with {link.ownership_pct}% ownership"],
            "chain": [f"TAXPAYER:{taxpayer.id}", f"BENEFICIAL_OWNER:{bo.id}"],
        })

    # --- Signal B: Indirect ownership (multi-hop) via OWNERSHIP rels ---
    rels = _get_all_relationships(db, year)
    # Build reverse ownership: who owns the taxpayer?
    reverse_adj: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for r in rels:
        if r.relationship_type == RelationshipType.OWNERSHIP:
            dst = f"{r.to_entity_type.value}:{r.to_entity_id}"
            src = f"{r.from_entity_type.value}:{r.from_entity_id}"
            pct = float(r.pct or 0)
            reverse_adj[dst].append((src, pct))

    root_key = f"TAXPAYER:{taxpayer.id}"
    # BFS upward
    upstream: Dict[str, Tuple[float, List[str]]] = {root_key: (100.0, [root_key])}
    queue: deque = deque([(root_key, 100.0, [root_key], 0)])
    while queue:
        node, eff, path, depth = queue.popleft()
        if depth >= 4:
            continue
        for parent, pct in reverse_adj.get(node, []):
            parent_eff = eff * (pct / 100.0) if pct > 0 else eff * 0.5
            if parent not in upstream or parent_eff > upstream[parent][0]:
                upstream[parent] = (parent_eff, path + [parent])
                queue.append((parent, parent_eff, path + [parent], depth + 1))

    for node_key, (eff, path) in upstream.items():
        if node_key == root_key:
            continue
        parts = node_key.split(":")
        etype, eid = parts[0], int(parts[1])
        if etype == "BENEFICIAL_OWNER":
            # Already captured as direct
            continue
        conf = min(0.9, eff / 100.0 * 0.8)
        if conf >= min_confidence:
            candidates.append({
                "entity_type": etype,
                "entity_id": eid,
                "name": _node_label(db, EntityType(etype), eid),
                "inferred": True,
                "confidence": round(conf, 3),
                "effective_ownership_pct": round(eff, 3),
                "evidence": [f"Indirect ownership chain ({eff:.1f}% effective)"],
                "chain": path,
            })

    # Sort by confidence desc
    candidates.sort(key=lambda c: c["confidence"], reverse=True)

    risk_score = 0.2 if not direct_bos else 0.0
    risk_score += min(0.5, len(candidates) * 0.1)

    return {
        "detection_type": "BENEFICIAL_OWNER_INFERENCE",
        "root_npwp": root_npwp,
        "root_entity_id": taxpayer.id,
        "tax_year": year,
        "candidates": candidates[:20],
        "direct_bo_count": len(direct_bos),
        "inferred_count": sum(1 for c in candidates if c.get("inferred")),
        "risk_score": round(risk_score, 3),
        "risk_level": _score_to_level(risk_score),
        "summary": (
            f"Found {len(direct_bos)} direct and {sum(1 for c in candidates if c.get('inferred'))} "
            f"inferred probable beneficial owners for {taxpayer.name} ({root_npwp})."
        ),
        "evidence": {"candidates": candidates[:10]},
    }


# ---------------------------------------------------------------------------
# 4. VAT Carousel Detection
# ---------------------------------------------------------------------------

def detect_vat_carousel(
    db: Session,
    root_npwp: str,
    year: int,
) -> Dict[str, Any]:
    """
    Detect potential VAT carousel patterns using heuristics:
    - Circular invoice/affiliation transaction chains
    - High affiliate transaction throughput relative to substance
    - Short-chain repeated counterparties
    """
    taxpayer = _resolve_taxpayer(db, root_npwp)
    if not taxpayer:
        return {"error": f"Taxpayer with NPWP {root_npwp!r} not found"}

    # Get relationship-based circular patterns
    circular_result = detect_circular_transactions(db, root_npwp, year, max_depth=4)
    cycles = circular_result.get("cycles", [])

    # Get affiliate transactions for the taxpayer group
    financials = (
        db.query(TaxpayerYearlyFinancial)
        .filter(TaxpayerYearlyFinancial.taxpayer_id == taxpayer.id,
                TaxpayerYearlyFinancial.tax_year == year)
        .first()
    )
    aff_txs = (
        db.query(TaxpayerYearlyAffiliateTx)
        .filter(TaxpayerYearlyAffiliateTx.taxpayer_id == taxpayer.id,
                TaxpayerYearlyAffiliateTx.tax_year == year)
        .all()
    )

    total_affiliate = sum(float(tx.tx_value or 0) for tx in aff_txs)
    turnover = float(financials.turnover or 0) if financials else 0.0

    # Heuristic signals
    signals = []
    risk_score = 0.0

    if cycles:
        signals.append({
            "code": "CIRCULAR_RELATIONSHIP_CHAIN",
            "description": f"{len(cycles)} circular relationship chains detected",
            "value": len(cycles),
        })
        risk_score += min(0.4, len(cycles) * 0.1)

    if turnover > 0 and total_affiliate / max(turnover, 1) > 0.5:
        ratio = total_affiliate / turnover
        signals.append({
            "code": "HIGH_AFFILIATE_TO_TURNOVER_RATIO",
            "description": f"Affiliate transactions are {ratio:.0%} of turnover",
            "value": round(ratio, 3),
        })
        risk_score += min(0.35, ratio * 0.25)

    if len(aff_txs) > 10:
        signals.append({
            "code": "HIGH_AFFILIATE_TRANSACTION_COUNT",
            "description": f"{len(aff_txs)} affiliate transactions in {year}",
            "value": len(aff_txs),
        })
        risk_score += 0.1

    return {
        "detection_type": "VAT_CAROUSEL",
        "root_npwp": root_npwp,
        "root_entity_id": taxpayer.id,
        "tax_year": year,
        "signals": signals,
        "circular_chains": cycles[:5],
        "total_affiliate_value": total_affiliate,
        "turnover": turnover,
        "risk_score": round(min(1.0, risk_score), 3),
        "risk_level": _score_to_level(risk_score),
        "summary": (
            f"VAT carousel analysis for {taxpayer.name} ({root_npwp}) in {year}. "
            f"{len(signals)} risk signal(s) detected."
        ),
        "reason_codes": [s["code"] for s in signals],
        "evidence": {"signals": signals, "circular_chains": cycles[:5]},
    }


# ---------------------------------------------------------------------------
# 5. Shell Company Detection
# ---------------------------------------------------------------------------

def detect_shell_company(
    db: Session,
    root_npwp: str,
    year: int,
) -> Dict[str, Any]:
    """
    Score a taxpayer entity on shell-company indicators using composite
    substance heuristics.
    """
    taxpayer = _resolve_taxpayer(db, root_npwp)
    if not taxpayer:
        return {"error": f"Taxpayer with NPWP {root_npwp!r} not found"}

    signals = []
    risk_score = 0.0

    # Officer / director count via CONTROL relationships
    rels = _get_all_relationships(db, year)
    officer_rels = [
        r for r in rels
        if r.to_entity_type == EntityType.TAXPAYER
        and r.to_entity_id == taxpayer.id
        and r.from_entity_type == EntityType.OFFICER
    ]
    officer_count = len(officer_rels)

    if officer_count == 0:
        signals.append({"code": "NO_REGISTERED_OFFICERS", "description": "No officers linked", "value": 0})
        risk_score += 0.25
    elif officer_count == 1:
        signals.append({"code": "SINGLE_OFFICER", "description": "Only 1 officer linked", "value": 1})
        risk_score += 0.10

    # Financial substance
    financials = (
        db.query(TaxpayerYearlyFinancial)
        .filter(TaxpayerYearlyFinancial.taxpayer_id == taxpayer.id,
                TaxpayerYearlyFinancial.tax_year == year)
        .first()
    )
    if not financials:
        signals.append({"code": "NO_FINANCIAL_DATA", "description": f"No financial data for {year}", "value": None})
        risk_score += 0.20
    elif float(financials.turnover or 0) == 0:
        signals.append({"code": "ZERO_TURNOVER", "description": "Zero declared turnover", "value": 0})
        risk_score += 0.20

    # Affiliate transaction concentration
    aff_txs = (
        db.query(TaxpayerYearlyAffiliateTx)
        .filter(TaxpayerYearlyAffiliateTx.taxpayer_id == taxpayer.id,
                TaxpayerYearlyAffiliateTx.tax_year == year)
        .all()
    )
    total_aff = sum(float(tx.tx_value or 0) for tx in aff_txs)
    turnover = float(financials.turnover or 0) if financials else 0.0
    if turnover > 0 and total_aff / turnover > 0.8:
        signals.append({
            "code": "HIGH_AFFILIATE_CONCENTRATION",
            "description": f"{total_aff/turnover:.0%} of turnover is affiliate transactions",
            "value": round(total_aff / turnover, 3),
        })
        risk_score += 0.20

    # Ownership opacity: owned by non-TAXPAYER entities
    owner_rels = [
        r for r in rels
        if r.to_entity_type == EntityType.TAXPAYER
        and r.to_entity_id == taxpayer.id
        and r.relationship_type == RelationshipType.OWNERSHIP
    ]
    non_local_owners = [r for r in owner_rels if r.from_entity_type != EntityType.TAXPAYER]
    if non_local_owners:
        opacity = len(non_local_owners) / max(1, len(owner_rels))
        if opacity >= 0.5:
            signals.append({
                "code": "HIGH_OWNERSHIP_OPACITY",
                "description": f"{len(non_local_owners)} of {len(owner_rels)} owners are non-taxpayer entities",
                "value": round(opacity, 3),
            })
            risk_score += 0.15

    return {
        "detection_type": "SHELL_COMPANY",
        "root_npwp": root_npwp,
        "root_entity_id": taxpayer.id,
        "tax_year": year,
        "signals": signals,
        "officer_count": officer_count,
        "turnover": turnover,
        "affiliate_total": total_aff,
        "risk_score": round(min(1.0, risk_score), 3),
        "risk_level": _score_to_level(risk_score),
        "summary": (
            f"Shell company analysis for {taxpayer.name} ({root_npwp}) in {year}. "
            f"Score {min(1.0, risk_score):.2f} – {_score_to_level(risk_score)}."
        ),
        "reason_codes": [s["code"] for s in signals],
        "evidence": {"signals": signals},
    }


# ---------------------------------------------------------------------------
# 6. Nominee Director Detection
# ---------------------------------------------------------------------------

def detect_nominee_director(
    db: Session,
    year: int,
    min_entities: int = 3,
) -> Dict[str, Any]:
    """
    Detect officers who appear as director/commissioner across an unusually
    high number of entities – a common nominee-director pattern.
    """
    rels = _get_all_relationships(db, year)

    # Count entities per officer via CONTROL relationships
    officer_entity_map: Dict[int, Set[int]] = defaultdict(set)
    for r in rels:
        if (
            r.from_entity_type == EntityType.OFFICER
            and r.to_entity_type == EntityType.TAXPAYER
            and r.relationship_type in (RelationshipType.CONTROL, RelationshipType.OWNERSHIP)
        ):
            officer_entity_map[r.from_entity_id].add(r.to_entity_id)

    suspects = []
    for officer_id, entity_ids in officer_entity_map.items():
        if len(entity_ids) < min_entities:
            continue
        officer = db.query(Officer).filter(Officer.id == officer_id).first()
        name = officer.name if officer else f"OFFICER:{officer_id}"
        position = officer.position if officer else "Unknown"
        count = len(entity_ids)
        risk = min(1.0, (count - min_entities + 1) * 0.15)
        suspects.append({
            "officer_id": officer_id,
            "name": name,
            "position": position,
            "entity_count": count,
            "entity_ids": list(entity_ids)[:20],
            "nominee_risk_score": round(risk, 3),
            "risk_level": _score_to_level(risk),
        })

    suspects.sort(key=lambda x: x["entity_count"], reverse=True)

    overall_risk = min(1.0, len(suspects) * 0.2) if suspects else 0.0
    return {
        "detection_type": "NOMINEE_DIRECTOR",
        "tax_year": year,
        "suspects": suspects[:20],
        "suspect_count": len(suspects),
        "min_entities_threshold": min_entities,
        "risk_score": round(overall_risk, 3),
        "risk_level": _score_to_level(overall_risk),
        "summary": (
            f"{len(suspects)} officer(s) appear as director/controller in "
            f"≥{min_entities} entities in {year}, suggesting possible nominee patterns."
        ),
        "reason_codes": ["HIGH_DIRECTORSHIP_COUNT"] if suspects else [],
        "evidence": {"suspects": suspects[:10]},
    }


# ---------------------------------------------------------------------------
# 7. AI-Assisted Graph Discovery
# ---------------------------------------------------------------------------

def ai_discovery(
    db: Session,
    root_npwp: str,
    year: int,
) -> Dict[str, Any]:
    """
    Surface hidden or interesting relationships not immediately obvious from
    direct edges.  Returns a list of discovery signals with evidence.

    This is a rule-based analytic discovery engine (not generative AI).
    Signals include: shared addresses, shared BOs, overlapping directors,
    high-centrality pass-through nodes, and indirect ownership convergence.
    """
    taxpayer = _resolve_taxpayer(db, root_npwp)
    if not taxpayer:
        return {"error": f"Taxpayer with NPWP {root_npwp!r} not found"}

    rels = _get_all_relationships(db, year)
    findings: List[Dict] = []

    # --- A: Shared beneficial owner across multiple taxpayers ----------------
    # Find all taxpayers who share any BO with the root taxpayer
    root_bo_ids = {
        r.from_entity_id
        for r in rels
        if r.to_entity_type == EntityType.TAXPAYER
        and r.to_entity_id == taxpayer.id
        and r.from_entity_type == EntityType.BENEFICIAL_OWNER
    }
    if root_bo_ids:
        shared_tp_ids: Dict[int, Set[int]] = defaultdict(set)  # tp_id -> shared bo ids
        for r in rels:
            if (
                r.from_entity_type == EntityType.BENEFICIAL_OWNER
                and r.from_entity_id in root_bo_ids
                and r.to_entity_type == EntityType.TAXPAYER
                and r.to_entity_id != taxpayer.id
            ):
                shared_tp_ids[r.to_entity_id].add(r.from_entity_id)
        for tp_id, bo_ids in shared_tp_ids.items():
            tp = db.query(Taxpayer).filter(Taxpayer.id == tp_id).first()
            findings.append({
                "signal": "SHARED_BENEFICIAL_OWNER",
                "description": f"Shares {len(bo_ids)} beneficial owner(s) with {tp.name if tp else tp_id}",
                "confidence": 0.80,
                "entities_involved": [f"TAXPAYER:{taxpayer.id}", f"TAXPAYER:{tp_id}"],
                "evidence": f"Shared BO ID(s): {list(bo_ids)[:5]}",
            })

    # --- B: Shared officers --------------------------------------------------
    root_officer_ids = {
        r.from_entity_id
        for r in rels
        if r.from_entity_type == EntityType.OFFICER
        and r.to_entity_type == EntityType.TAXPAYER
        and r.to_entity_id == taxpayer.id
    }
    if root_officer_ids:
        shared_officer_map: Dict[int, Set[int]] = defaultdict(set)
        for r in rels:
            if (
                r.from_entity_type == EntityType.OFFICER
                and r.from_entity_id in root_officer_ids
                and r.to_entity_type == EntityType.TAXPAYER
                and r.to_entity_id != taxpayer.id
            ):
                shared_officer_map[r.to_entity_id].add(r.from_entity_id)
        for tp_id, off_ids in shared_officer_map.items():
            tp = db.query(Taxpayer).filter(Taxpayer.id == tp_id).first()
            findings.append({
                "signal": "SHARED_OFFICERS",
                "description": f"Shares {len(off_ids)} officer(s) with {tp.name if tp else tp_id}",
                "confidence": 0.70,
                "entities_involved": [f"TAXPAYER:{taxpayer.id}", f"TAXPAYER:{tp_id}"],
                "evidence": f"Shared officer ID(s): {list(off_ids)[:5]}",
            })

    # --- C: High-centrality pass-through nodes in ego network ---------------
    # Count connections for each node in 2-hop neighbourhood
    from collections import Counter
    degree_count: Counter = Counter()
    for r in rels:
        if (
            (r.from_entity_type == EntityType.TAXPAYER and r.from_entity_id == taxpayer.id)
            or (r.to_entity_type == EntityType.TAXPAYER and r.to_entity_id == taxpayer.id)
        ):
            other_key = (
                f"{r.to_entity_type.value}:{r.to_entity_id}"
                if r.from_entity_type == EntityType.TAXPAYER and r.from_entity_id == taxpayer.id
                else f"{r.from_entity_type.value}:{r.from_entity_id}"
            )
            degree_count[other_key] += 1

    # High-degree nodes relative to mean
    if degree_count:
        mean_deg = sum(degree_count.values()) / len(degree_count)
        for node_key, deg in degree_count.most_common(5):
            if deg > mean_deg * 2:
                findings.append({
                    "signal": "HIGH_CENTRALITY_NODE",
                    "description": f"Node {node_key} has {deg} connections (mean: {mean_deg:.1f})",
                    "confidence": 0.65,
                    "entities_involved": [f"TAXPAYER:{taxpayer.id}", node_key],
                    "evidence": f"Connection degree: {deg}",
                })

    # --- D: Indirect ownership convergence ----------------------------------
    pyramid_result = detect_ownership_pyramid(db, root_npwp, year, max_depth=3)
    if not pyramid_result.get("error") and pyramid_result.get("controlled_entities_count", 0) > 3:
        findings.append({
            "signal": "OWNERSHIP_CONCENTRATION",
            "description": (
                f"Root entity controls ≥{pyramid_result['controlled_entities_count']} "
                f"downstream entities with >25% effective ownership"
            ),
            "confidence": 0.85,
            "entities_involved": [f"TAXPAYER:{taxpayer.id}"],
            "evidence": f"Ownership pyramid depth: {pyramid_result.get('max_chain_depth', 0)}",
        })

    # Sort by confidence
    findings.sort(key=lambda f: f["confidence"], reverse=True)
    risk_score = min(1.0, len(findings) * 0.15)

    return {
        "detection_type": "AI_DISCOVERY",
        "root_npwp": root_npwp,
        "root_entity_id": taxpayer.id,
        "tax_year": year,
        "findings": findings,
        "finding_count": len(findings),
        "risk_score": round(risk_score, 3),
        "risk_level": _score_to_level(risk_score),
        "summary": (
            f"Graph discovery for {taxpayer.name} ({root_npwp}) surfaced "
            f"{len(findings)} signal(s) across {year}."
        ),
        "evidence": {"findings": findings[:15]},
    }


# ---------------------------------------------------------------------------
# Path analysis (NPWP-pair mode)
# ---------------------------------------------------------------------------

def find_shortest_path(
    db: Session,
    npwp1: str,
    npwp2: str,
    year: int,
    max_depth: int = 5,
) -> Dict[str, Any]:
    """
    Find shortest relationship path between two taxpayers using BFS.
    """
    tp1 = _resolve_taxpayer(db, npwp1)
    tp2 = _resolve_taxpayer(db, npwp2)
    if not tp1:
        return {"error": f"Taxpayer with NPWP {npwp1!r} not found"}
    if not tp2:
        return {"error": f"Taxpayer with NPWP {npwp2!r} not found"}
    if tp1.id == tp2.id:
        return {"path": [f"TAXPAYER:{tp1.id}"], "hop_count": 0, "same_entity": True}

    rels = _get_all_relationships(db, year)
    # Undirected adjacency
    adj: Dict[str, Set[str]] = defaultdict(set)
    for r in rels:
        src = f"{r.from_entity_type.value}:{r.from_entity_id}"
        dst = f"{r.to_entity_type.value}:{r.to_entity_id}"
        adj[src].add(dst)
        adj[dst].add(src)

    start = f"TAXPAYER:{tp1.id}"
    end = f"TAXPAYER:{tp2.id}"
    # BFS
    queue: deque = deque([(start, [start])])
    visited = {start}
    while queue:
        node, path = queue.popleft()
        if len(path) > max_depth + 1:
            break
        for neighbor in adj.get(node, set()):
            if neighbor == end:
                final_path = path + [neighbor]
                return {
                    "path": final_path,
                    "hop_count": len(final_path) - 1,
                    "npwp1": npwp1,
                    "npwp2": npwp2,
                    "entity1_id": tp1.id,
                    "entity2_id": tp2.id,
                    "entity1_name": tp1.name,
                    "entity2_name": tp2.name,
                    "path_type": _classify_path(final_path),
                }
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    return {
        "path": None,
        "hop_count": None,
        "npwp1": npwp1,
        "npwp2": npwp2,
        "entity1_id": tp1.id,
        "entity2_id": tp2.id,
        "entity1_name": tp1.name,
        "entity2_name": tp2.name,
        "connected": False,
        "message": f"No path found within {max_depth} hops",
    }


def _classify_path(path: List[str]) -> str:
    types = {n.split(":")[0] for n in path}
    if "BENEFICIAL_OWNER" in types:
        return "OWNERSHIP_VIA_BENEFICIAL_OWNER"
    if "OFFICER" in types:
        return "MANAGEMENT_LINK"
    if all(t == "TAXPAYER" for t in types):
        return "DIRECT_OWNERSHIP"
    return "MIXED"


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _score_to_level(score: float) -> str:
    if score >= 0.75:
        return "VERY_HIGH"
    if score >= 0.5:
        return "HIGH"
    if score >= 0.25:
        return "MEDIUM"
    return "LOW"
