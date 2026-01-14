from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel

from app.db.session import get_db
from app.api.deps import get_current_user, get_current_active_analyst
from app.db.models import Group, GroupMembership
from app.services.aggregate_service import AggregateService

router = APIRouter(prefix="/groups", tags=["groups"])


class GroupResponse(BaseModel):
    id: int
    name: str
    sector: Optional[str]
    notes: Optional[str]
    member_count: int = 0

    class Config:
        from_attributes = True


class GroupDetailResponse(BaseModel):
    id: int
    name: str
    sector: Optional[str]
    notes: Optional[str]
    member_count: int
    members: List[dict]
    aggregates: dict

    class Config:
        from_attributes = True


@router.get("", response_model=List[GroupResponse])
def list_groups(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all groups with pagination."""
    groups = (
        db.query(Group)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    result = []
    for group in groups:
        member_count = db.query(GroupMembership).filter(GroupMembership.group_id == group.id).count()
        result.append(GroupResponse(
            id=group.id,
            name=group.name,
            sector=group.sector,
            notes=group.notes,
            member_count=member_count
        ))

    return result


@router.get("/{group_id}", response_model=GroupDetailResponse)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get group detail with members and aggregates."""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Get members
    memberships = (
        db.query(GroupMembership)
        .options(joinedload(GroupMembership.taxpayer))
        .filter(GroupMembership.group_id == group_id)
        .all()
    )

    members = [
        {
            "id": m.taxpayer.id,
            "name": m.taxpayer.name,
            "npwp_masked": m.taxpayer.npwp_masked,
            "role": m.role,
            "status": m.taxpayer.status
        }
        for m in memberships
    ]

    # Get aggregates
    aggregates = AggregateService.get_group_aggregates(db, group_id)

    return GroupDetailResponse(
        id=group.id,
        name=group.name,
        sector=group.sector,
        notes=group.notes,
        member_count=len(members),
        members=members,
        aggregates=aggregates
    )
