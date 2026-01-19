from enum import Enum
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.db.models import BeneficialOwner, EntityType, Taxpayer, UserAccount, UserRole, Officer, Address, Intermediary
from app.services.network_service import build_network_graph, build_network_layer_stats


router = APIRouter(prefix="/network", tags=["network"])


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


def _get_role_max_nodes(user: UserAccount) -> int:
    if user.role == UserRole.ADMIN:
        return 1500
    if user.role == UserRole.ANALYST:
        return 1200
    return 600


def _validate_root(db: Session, root_type: RootEntityType, root_id: int) -> None:
    if root_type == RootEntityType.TAXPAYER:
        exists = db.query(Taxpayer.id).filter(Taxpayer.id == root_id).first()
    elif root_type == RootEntityType.BENEFICIAL_OWNER:
        exists = db.query(BeneficialOwner.id).filter(BeneficialOwner.id == root_id).first()
    elif root_type == RootEntityType.OFFICER:
        exists = db.query(Officer.id).filter(Officer.id == root_id).first()
    elif root_type == RootEntityType.ADDRESS:
        exists = db.query(Address.id).filter(Address.id == root_id).first()
    elif root_type == RootEntityType.INTERMEDIARY:
        exists = db.query(Intermediary.id).filter(Intermediary.id == root_id).first()
    else:
        exists = None

    if not exists:
        raise HTTPException(status_code=404, detail="Root entity not found")


@router.get("/graph", response_model=NetworkGraphResponse)
def get_network_graph(
    root_type: RootEntityType = Query(...),
    root_id: int = Query(..., ge=1),
    year: int = Query(..., ge=1990, le=2100),
    depth: int = Query(2, ge=1, le=5),
    max_nodes: int = Query(300, ge=1),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user)
):
    """Return a bounded network graph for a root entity."""
    role_max = _get_role_max_nodes(current_user)
    if max_nodes > role_max:
        raise HTTPException(
            status_code=400,
            detail=f"max_nodes exceeds role limit ({role_max})"
        )

    _validate_root(db, root_type, root_id)

    data = build_network_graph(
        db=db,
        root_type=EntityType(root_type.value),
        root_id=root_id,
        year=year,
        depth=depth,
        max_nodes=max_nodes
    )

    return NetworkGraphResponse(
        root_type=root_type.value,
        root_id=root_id,
        year=year,
        depth=depth,
        max_nodes=max_nodes,
        truncated=data["truncated"],
        layer_counts=data["layer_counts"],
        nodes=data["nodes"],
        edges=data["edges"]
    )


@router.get("/graph/stats", response_model=NetworkLayerStatsResponse)
def get_network_graph_stats(
    root_type: RootEntityType = Query(...),
    root_id: int = Query(..., ge=1),
    year: int = Query(..., ge=1990, le=2100),
    depth: int = Query(2, ge=1, le=5),
    max_nodes: int = Query(300, ge=1),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user)
):
    """Return layer counts for a bounded network graph."""
    role_max = _get_role_max_nodes(current_user)
    if max_nodes > role_max:
        raise HTTPException(
            status_code=400,
            detail=f"max_nodes exceeds role limit ({role_max})"
        )

    _validate_root(db, root_type, root_id)

    data = build_network_layer_stats(
        db=db,
        root_type=EntityType(root_type.value),
        root_id=root_id,
        year=year,
        depth=depth,
        max_nodes=max_nodes
    )

    return NetworkLayerStatsResponse(
        root_type=root_type.value,
        root_id=root_id,
        year=year,
        depth=depth,
        max_nodes=max_nodes,
        truncated=data["truncated"],
        layer_counts=data["layer_counts"]
    )


class ExpandRequest(BaseModel):
    """Request model for node expansion."""
    pass


class ExpandResponse(BaseModel):
    """Response model for node expansion."""
    nodes: List[NetworkNode]
    edges: List[NetworkEdge]
    truncated: bool
    layer_counts: Dict[int, int]


@router.get("/expand", response_model=ExpandResponse)
def expand_node(
    node_type: RootEntityType = Query(...),
    node_id: int = Query(..., ge=1),
    year: int = Query(..., ge=1990, le=2100),
    depth: int = Query(1, ge=1, le=2),
    edge_types: Optional[str] = Query(None, description="Comma-separated edge types to include"),
    max_neighbors: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user)
):
    """
    Expand a single node to get its immediate neighbors.
    Used for ICIJ-like double-click expansion.
    """
    _validate_root(db, node_type, node_id)

    # Build graph starting from this node with depth 1
    data = build_network_graph(
        db=db,
        root_type=EntityType(node_type.value),
        root_id=node_id,
        year=year,
        depth=depth,
        max_nodes=max_neighbors
    )

    return ExpandResponse(
        nodes=data["nodes"],
        edges=data["edges"],
        truncated=data["truncated"],
        layer_counts=data["layer_counts"]
    )


@router.get("/search-npwp")
def search_by_npwp(
    npwp: str = Query(..., min_length=1),
    year: int = Query(..., ge=1990, le=2100),
    depth: int = Query(2, ge=1, le=5),
    edge_types: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user)
):
    """
    Search for a taxpayer by NPWP and return its network graph.
    """
    # Clean NPWP (remove dots and dashes)
    clean_npwp = npwp.replace(".", "").replace("-", "")

    # Search for taxpayer by NPWP pattern
    taxpayer = db.query(Taxpayer).filter(
        Taxpayer.npwp_masked.ilike(f"%{clean_npwp}%")
    ).first()

    if not taxpayer:
        raise HTTPException(
            status_code=404,
            detail=f"Taxpayer with NPWP '{npwp}' not found"
        )

    role_max = _get_role_max_nodes(current_user)

    data = build_network_graph(
        db=db,
        root_type=EntityType.TAXPAYER,
        root_id=taxpayer.id,
        year=year,
        depth=depth,
        max_nodes=min(300, role_max)
    )

    return NetworkGraphResponse(
        root_type="TAXPAYER",
        root_id=taxpayer.id,
        year=year,
        depth=depth,
        max_nodes=min(300, role_max),
        truncated=data["truncated"],
        layer_counts=data["layer_counts"],
        nodes=data["nodes"],
        edges=data["edges"]
    )
