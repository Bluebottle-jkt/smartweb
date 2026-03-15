"""
Network / Graph Intelligence Router
=====================================
Endpoints for graph search, pair-path analysis, and all graph intelligence
detectors.  RBAC is enforced via get_current_user dependency.
All sensitive actions are written to the audit log.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_analyst, get_current_user
from app.db.models import (
    AuditLog,
    BeneficialOwner,
    EntityType,
    Taxpayer,
    UserAccount,
    UserRole,
    Officer,
    Address,
    Intermediary,
)
from app.db.neo4j import is_neo4j_available
from app.db.session import get_db
from app.services.graph_intelligence_service import (
    ai_discovery,
    detect_circular_transactions,
    detect_nominee_director,
    detect_ownership_pyramid,
    detect_shell_company,
    detect_vat_carousel,
    find_shortest_path,
    infer_beneficial_owners,
)
from app.services.network_service import build_network_graph, build_network_layer_stats

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/network", tags=["network"])


# ---------------------------------------------------------------------------
# Shared schemas & helpers (kept from original)
# ---------------------------------------------------------------------------

class RootEntityType(str, Enum):
    TAXPAYER = "TAXPAYER"
    BENEFICIAL_OWNER = "BENEFICIAL_OWNER"
    OFFICER = "OFFICER"
    ADDRESS = "ADDRESS"
    INTERMEDIARY = "INTERMEDIARY"


class NetworkNode(BaseModel):
    id: str
    entity_id: int
    entity_type: str
    entity_subtype: Optional[str] = None
    name: str
    npwp: Optional[str] = None
    location_label: str
    layer: int
    category: Optional[str] = None


class NetworkEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship_type: str
    label: str
    layer: int
    pct: Optional[float] = None
    confidence: Optional[float] = None
    notes: Optional[str] = None
    source_ref: Optional[str] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None


class NetworkGraphResponse(BaseModel):
    root_type: str
    root_id: int
    year: int
    depth: int
    max_nodes: int
    truncated: bool
    layer_counts: Dict[int, int]
    nodes: List[NetworkNode]
    edges: List[NetworkEdge]


class NetworkLayerStatsResponse(BaseModel):
    root_type: str
    root_id: int
    year: int
    depth: int
    max_nodes: int
    truncated: bool
    layer_counts: Dict[int, int]


class ExpandResponse(BaseModel):
    nodes: List[NetworkNode]
    edges: List[NetworkEdge]
    truncated: bool
    layer_counts: Dict[int, int]


def _get_role_max_nodes(user: UserAccount) -> int:
    if user.role == UserRole.ADMIN:
        return 1500
    if user.role == UserRole.ANALYST:
        return 1200
    return 600


def _validate_root(db: Session, root_type: RootEntityType, root_id: int) -> None:
    model_map = {
        RootEntityType.TAXPAYER: Taxpayer,
        RootEntityType.BENEFICIAL_OWNER: BeneficialOwner,
        RootEntityType.OFFICER: Officer,
        RootEntityType.ADDRESS: Address,
        RootEntityType.INTERMEDIARY: Intermediary,
    }
    model = model_map.get(root_type)
    if not model:
        raise HTTPException(status_code=400, detail="Invalid root entity type")
    exists = db.query(model.id).filter(model.id == root_id).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Root entity not found")


def _audit(
    db: Session,
    user: UserAccount,
    action: str,
    entity_type: str,
    payload: Dict,
) -> None:
    try:
        db.add(AuditLog(
            actor_user_id=user.id,
            action=action,
            entity_type=entity_type,
            payload=payload,
        ))
        db.commit()
    except Exception:
        db.rollback()


# ---------------------------------------------------------------------------
# Original endpoints (preserved exactly)
# ---------------------------------------------------------------------------

@router.get("/graph", response_model=NetworkGraphResponse)
def get_network_graph(
    root_type: RootEntityType = Query(...),
    root_id: int = Query(..., ge=1),
    year: int = Query(..., ge=1990, le=2100),
    depth: int = Query(2, ge=1, le=5),
    max_nodes: int = Query(300, ge=1),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    """Return a bounded network graph for a root entity."""
    role_max = _get_role_max_nodes(current_user)
    if max_nodes > role_max:
        raise HTTPException(status_code=400, detail=f"max_nodes exceeds role limit ({role_max})")

    _validate_root(db, root_type, root_id)
    data = build_network_graph(
        db=db, root_type=EntityType(root_type.value),
        root_id=root_id, year=year, depth=depth, max_nodes=max_nodes,
    )
    return NetworkGraphResponse(
        root_type=root_type.value, root_id=root_id, year=year, depth=depth,
        max_nodes=max_nodes, truncated=data["truncated"],
        layer_counts=data["layer_counts"], nodes=data["nodes"], edges=data["edges"],
    )


@router.get("/graph/stats", response_model=NetworkLayerStatsResponse)
def get_network_graph_stats(
    root_type: RootEntityType = Query(...),
    root_id: int = Query(..., ge=1),
    year: int = Query(..., ge=1990, le=2100),
    depth: int = Query(2, ge=1, le=5),
    max_nodes: int = Query(300, ge=1),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    """Return layer counts for a bounded network graph."""
    role_max = _get_role_max_nodes(current_user)
    if max_nodes > role_max:
        raise HTTPException(status_code=400, detail=f"max_nodes exceeds role limit ({role_max})")
    _validate_root(db, root_type, root_id)
    data = build_network_layer_stats(
        db=db, root_type=EntityType(root_type.value),
        root_id=root_id, year=year, depth=depth, max_nodes=max_nodes,
    )
    return NetworkLayerStatsResponse(
        root_type=root_type.value, root_id=root_id, year=year, depth=depth,
        max_nodes=max_nodes, truncated=data["truncated"], layer_counts=data["layer_counts"],
    )


@router.get("/expand", response_model=ExpandResponse)
def expand_node(
    node_type: RootEntityType = Query(...),
    node_id: int = Query(..., ge=1),
    year: int = Query(..., ge=1990, le=2100),
    depth: int = Query(1, ge=1, le=2),
    edge_types: Optional[str] = Query(None),
    max_neighbors: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    """Expand a single node to get its immediate neighbours (ICIJ double-click)."""
    _validate_root(db, node_type, node_id)
    data = build_network_graph(
        db=db, root_type=EntityType(node_type.value),
        root_id=node_id, year=year, depth=depth, max_nodes=max_neighbors,
    )
    return ExpandResponse(
        nodes=data["nodes"], edges=data["edges"],
        truncated=data["truncated"], layer_counts=data["layer_counts"],
    )


def _npwp_filter(npwp: str):
    """Build an ILIKE filter that works with masked NPWPs like '17.***.***.*-***.100'.
    Extracts digit groups from the query and builds a pattern that bridges the mask chars."""
    import re
    groups = re.findall(r'\d+', npwp)
    if len(groups) >= 2:
        return Taxpayer.npwp_masked.ilike(f"%{groups[0]}%{groups[-1]}%")
    if len(groups) == 1:
        return Taxpayer.npwp_masked.ilike(f"%{groups[0]}%")
    clean = npwp.replace(".", "").replace("-", "")
    return Taxpayer.npwp_masked.ilike(f"%{clean}%")


@router.get("/search-npwp")
def search_by_npwp(
    npwp: str = Query(..., min_length=1),
    year: int = Query(..., ge=1990, le=2100),
    depth: int = Query(2, ge=1, le=5),
    edge_types: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    """Search for a taxpayer by NPWP and return its network graph."""
    taxpayer = db.query(Taxpayer).filter(_npwp_filter(npwp)).first()
    if not taxpayer:
        raise HTTPException(status_code=404, detail=f"Taxpayer with NPWP '{npwp}' not found")

    role_max = _get_role_max_nodes(current_user)
    data = build_network_graph(
        db=db, root_type=EntityType.TAXPAYER,
        root_id=taxpayer.id, year=year, depth=depth, max_nodes=min(300, role_max),
    )
    return NetworkGraphResponse(
        root_type="TAXPAYER", root_id=taxpayer.id, year=year, depth=depth,
        max_nodes=min(300, role_max), truncated=data["truncated"],
        layer_counts=data["layer_counts"], nodes=data["nodes"], edges=data["edges"],
    )


# ---------------------------------------------------------------------------
# New: POST /network/search  – primary graph search endpoint
# ---------------------------------------------------------------------------

class GraphSearchRequest(BaseModel):
    npwp: str = Field(..., description="NPWP of the primary taxpayer (required)")
    year: int = Field(..., ge=1990, le=2100, description="Tax year (required)")
    npwp2: Optional[str] = Field(None, description="NPWP of second entity for path analysis")
    depth: int = Field(2, ge=1, le=5)
    max_nodes: int = Field(300, ge=1, le=1500)
    relationship_types: Optional[List[str]] = None
    min_ownership_pct: Optional[float] = Field(None, ge=0, le=100)
    entity_types: Optional[List[str]] = None


class GraphSearchResponse(BaseModel):
    mode: str  # "ego" | "path"
    root_npwp: str
    root_entity_id: Optional[int] = None
    year: int
    depth: int
    graph: Optional[Dict[str, Any]] = None
    path_analysis: Optional[Dict[str, Any]] = None
    truncated: bool = False


@router.post("/search", response_model=GraphSearchResponse)
def graph_search(
    req: GraphSearchRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    """
    Primary graph search.  If npwp2 is provided, returns path analysis
    between the two entities.  Otherwise returns ego-network.
    """
    role_max = _get_role_max_nodes(current_user)
    max_nodes = min(req.max_nodes, role_max)

    _audit(db, current_user, "EXPORT", "GRAPH_SEARCH", {
        "npwp": req.npwp, "year": req.year, "npwp2": req.npwp2,
    })

    taxpayer = db.query(Taxpayer).filter(_npwp_filter(req.npwp)).first()
    if not taxpayer:
        raise HTTPException(status_code=404, detail=f"Taxpayer with NPWP '{req.npwp}' not found")

    # Path mode
    if req.npwp2:
        path_result = find_shortest_path(db, req.npwp, req.npwp2, req.year)
        data = build_network_graph(
            db=db, root_type=EntityType.TAXPAYER,
            root_id=taxpayer.id, year=req.year, depth=req.depth, max_nodes=max_nodes,
        )
        return GraphSearchResponse(
            mode="path", root_npwp=req.npwp, root_entity_id=taxpayer.id,
            year=req.year, depth=req.depth,
            graph={"nodes": data["nodes"], "edges": data["edges"],
                   "layer_counts": data["layer_counts"]},
            path_analysis=path_result,
            truncated=data["truncated"],
        )

    # Ego-network mode
    data = build_network_graph(
        db=db, root_type=EntityType.TAXPAYER,
        root_id=taxpayer.id, year=req.year, depth=req.depth, max_nodes=max_nodes,
    )
    return GraphSearchResponse(
        mode="ego", root_npwp=req.npwp, root_entity_id=taxpayer.id,
        year=req.year, depth=req.depth,
        graph={"nodes": data["nodes"], "edges": data["edges"],
               "layer_counts": data["layer_counts"]},
        truncated=data["truncated"],
    )


# ---------------------------------------------------------------------------
# New: POST /network/path
# ---------------------------------------------------------------------------

class PathRequest(BaseModel):
    npwp: str
    npwp2: str
    year: int = Field(..., ge=1990, le=2100)
    max_depth: int = Field(5, ge=1, le=7)


@router.post("/path")
def path_analysis(
    req: PathRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    """Find shortest relationship path between two taxpayers."""
    _audit(db, current_user, "EXPORT", "PATH_ANALYSIS",
           {"npwp": req.npwp, "npwp2": req.npwp2, "year": req.year})
    result = find_shortest_path(db, req.npwp, req.npwp2, req.year, req.max_depth)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# New: POST /network/export  (PNG – done on frontend; backend returns metadata)
# ---------------------------------------------------------------------------

class ExportRequest(BaseModel):
    npwp: str
    year: int
    depth: int = 2
    filters_used: Optional[Dict[str, Any]] = None


@router.post("/export")
def export_graph_metadata(
    req: ExportRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    """Log a graph export action and return export metadata for client-side PNG."""
    _audit(db, current_user, "EXPORT", "GRAPH_EXPORT",
           {"npwp": req.npwp, "year": req.year, "depth": req.depth})
    return {
        "npwp": req.npwp,
        "year": req.year,
        "depth": req.depth,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "exported_by": current_user.username,
        "filters_used": req.filters_used or {},
    }


# ---------------------------------------------------------------------------
# Graph Intelligence endpoints
# ---------------------------------------------------------------------------

class IntelligenceRequest(BaseModel):
    npwp: str
    year: int = Field(..., ge=1990, le=2100)
    max_depth: int = Field(5, ge=1, le=7)


@router.post("/ai-discovery")
def run_ai_discovery(
    req: IntelligenceRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_analyst),
):
    """Surface hidden relationships and suspicious clusters."""
    _audit(db, current_user, "EXPORT", "AI_DISCOVERY",
           {"npwp": req.npwp, "year": req.year})
    result = ai_discovery(db, req.npwp, req.year)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/ownership-pyramid")
def run_ownership_pyramid(
    req: IntelligenceRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_analyst),
):
    """Detect ownership pyramid and compute effective ownership."""
    _audit(db, current_user, "EXPORT", "OWNERSHIP_PYRAMID",
           {"npwp": req.npwp, "year": req.year})
    result = detect_ownership_pyramid(db, req.npwp, req.year, req.max_depth)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/circular-detection")
def run_circular_detection(
    req: IntelligenceRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_analyst),
):
    """Detect directed cycles in the relationship graph."""
    _audit(db, current_user, "EXPORT", "CIRCULAR_DETECTION",
           {"npwp": req.npwp, "year": req.year})
    result = detect_circular_transactions(db, req.npwp, req.year, req.max_depth)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/beneficial-owner-inference")
def run_bo_inference(
    req: IntelligenceRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_analyst),
):
    """Infer probable beneficial owners including indirect chains."""
    _audit(db, current_user, "EXPORT", "BO_INFERENCE",
           {"npwp": req.npwp, "year": req.year})
    result = infer_beneficial_owners(db, req.npwp, req.year)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/vat-carousel-detection")
def run_vat_carousel(
    req: IntelligenceRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_analyst),
):
    """Detect potential VAT carousel fraud patterns."""
    _audit(db, current_user, "EXPORT", "VAT_CAROUSEL",
           {"npwp": req.npwp, "year": req.year})
    result = detect_vat_carousel(db, req.npwp, req.year)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/shell-company-detection")
def run_shell_detection(
    req: IntelligenceRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_analyst),
):
    """Score an entity on shell-company risk indicators."""
    _audit(db, current_user, "EXPORT", "SHELL_COMPANY",
           {"npwp": req.npwp, "year": req.year})
    result = detect_shell_company(db, req.npwp, req.year)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


class NomineeRequest(BaseModel):
    year: int = Field(..., ge=1990, le=2100)
    min_entities: int = Field(3, ge=2, le=50)


@router.post("/nominee-director-detection")
def run_nominee_detection(
    req: NomineeRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_analyst),
):
    """Detect officers appearing as director/controller in many entities."""
    _audit(db, current_user, "EXPORT", "NOMINEE_DIRECTOR",
           {"year": req.year, "min_entities": req.min_entities})
    return detect_nominee_director(db, req.year, req.min_entities)


class TradeMispricingRequest(BaseModel):
    npwp: str
    year: int = Field(..., ge=1990, le=2100)
    hs_code: Optional[str] = None
    benchmark_price: Optional[float] = None


@router.post("/trade-mispricing-detection")
def run_trade_mispricing(
    req: TradeMispricingRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_analyst),
):
    """
    Trade mispricing detection stub.  Full implementation requires external
    price benchmark data.  Returns affiliate transaction profile as basis
    for mispricing assessment.
    """
    _audit(db, current_user, "EXPORT", "TRADE_MISPRICING",
           {"npwp": req.npwp, "year": req.year})

    tp = db.query(Taxpayer).filter(_npwp_filter(req.npwp)).first()
    if not tp:
        raise HTTPException(status_code=404, detail=f"Taxpayer '{req.npwp}' not found")

    from app.db.models import TaxpayerYearlyAffiliateTx
    txs = (
        db.query(TaxpayerYearlyAffiliateTx)
        .filter(TaxpayerYearlyAffiliateTx.taxpayer_id == tp.id,
                TaxpayerYearlyAffiliateTx.tax_year == req.year)
        .all()
    )
    total = sum(float(t.tx_value or 0) for t in txs)

    anomaly_score = 0.0
    signals = []
    if req.benchmark_price and total > req.benchmark_price * 1.5:
        anomaly_score = min(1.0, total / req.benchmark_price - 1)
        signals.append({
            "code": "ABOVE_BENCHMARK",
            "description": f"Affiliate total {total:,.0f} vs benchmark {req.benchmark_price:,.0f}",
            "value": round(anomaly_score, 3),
        })

    return {
        "detection_type": "TRADE_MISPRICING",
        "root_npwp": req.npwp,
        "root_entity_id": tp.id,
        "tax_year": req.year,
        "affiliate_tx_total": total,
        "transaction_count": len(txs),
        "benchmark_price": req.benchmark_price,
        "anomaly_score": round(anomaly_score, 3),
        "risk_level": "HIGH" if anomaly_score > 0.5 else "MEDIUM" if anomaly_score > 0.2 else "LOW",
        "signals": signals,
        "note": "Full benchmark integration requires external price reference data.",
    }


# ---------------------------------------------------------------------------
# Neo4j operational endpoints
# ---------------------------------------------------------------------------

@router.post("/sync/neo4j")
def trigger_neo4j_sync(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_analyst),
):
    """Trigger full Neo4j synchronisation in the background."""
    if not is_neo4j_available():
        return {"success": False, "reason": "Neo4j is not available or not enabled"}

    from app.services.neo4j_sync_service import sync_all

    def _run_sync():
        from app.db.session import SessionLocal
        db2 = SessionLocal()
        try:
            sync_all(db2)
        finally:
            db2.close()

    background_tasks.add_task(_run_sync)
    _audit(db, current_user, "CREATE", "NEO4J_SYNC", {})
    return {"success": True, "message": "Neo4j full sync started in background"}


@router.post("/sync/entity/{entity_type}/{entity_id}")
def sync_single_entity(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_analyst),
):
    """Sync a single entity to Neo4j."""
    if not is_neo4j_available():
        return {"success": False, "reason": "Neo4j is not available or not enabled"}
    from app.services.neo4j_sync_service import sync_entity
    return sync_entity(db, entity_type.upper(), entity_id)


@router.get("/health")
def graph_health(
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    """Health check for graph services."""
    from app.db.models import Relationship
    rel_count = db.query(Relationship).count()
    tp_count = db.query(Taxpayer).count()
    return {
        "status": "healthy",
        "neo4j_available": is_neo4j_available(),
        "postgresql_taxpayers": tp_count,
        "postgresql_relationships": rel_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
