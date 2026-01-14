from enum import Enum
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.db.models import BeneficialOwner, EntityType, Taxpayer, UserAccount, UserRole
from app.services.network_service import build_network_graph, build_network_layer_stats


router = APIRouter(prefix="/network", tags=["network"])


class RootEntityType(str, Enum):
    TAXPAYER = "TAXPAYER"
    BENEFICIAL_OWNER = "BENEFICIAL_OWNER"


class NetworkNode(BaseModel):
    id: str
    entity_id: int
    entity_type: str
    entity_subtype: Optional[str] = None
    name: str
    location_label: str
    layer: int


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
    else:
        exists = db.query(BeneficialOwner.id).filter(BeneficialOwner.id == root_id).first()

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
