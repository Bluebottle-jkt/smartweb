from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.api.deps import get_current_user
from app.db.models import BeneficialOwner, BeneficialOwnerTaxpayer, GroupMembership

router = APIRouter(prefix="/beneficial-owners", tags=["beneficial_owners"])


class BOListItem(BaseModel):
    id: int
    name: str
    id_number_masked: Optional[str]
    nationality: Optional[str]

    class Config:
        from_attributes = True


class BOListResponse(BaseModel):
    items: List[BOListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class BODetailResponse(BaseModel):
    id: int
    name: str
    id_number_masked: str | None
    nationality: str | None
    notes: str | None
    taxpayers: List[dict]
    groups: List[dict]

    class Config:
        from_attributes = True


@router.get("", response_model=BOListResponse)
def list_beneficial_owners(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    nationality: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List beneficial owners with pagination and filtering."""
    query = db.query(BeneficialOwner)

    # Apply filters
    if search:
        query = query.filter(
            (BeneficialOwner.name.ilike(f"%{search}%")) |
            (BeneficialOwner.id_number_masked.ilike(f"%{search}%"))
        )

    if nationality:
        query = query.filter(BeneficialOwner.nationality == nationality)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    items = query.order_by(BeneficialOwner.name).offset(offset).limit(page_size).all()

    total_pages = (total + page_size - 1) // page_size

    return BOListResponse(
        items=[BOListItem.from_orm(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{bo_id}")
def get_beneficial_owner(
    bo_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get beneficial owner detail with connected taxpayers and groups."""
    bo = db.query(BeneficialOwner).filter(BeneficialOwner.id == bo_id).first()
    if not bo:
        raise HTTPException(status_code=404, detail="Beneficial Owner not found")

    # Get taxpayers
    taxpayer_relationships = (
        db.query(BeneficialOwnerTaxpayer)
        .filter(BeneficialOwnerTaxpayer.beneficial_owner_id == bo_id)
        .all()
    )

    taxpayers_data = []
    group_ids_seen = set()

    for rel in taxpayer_relationships:
        taxpayer = rel.taxpayer
        taxpayers_data.append({
            "id": taxpayer.id,
            "name": taxpayer.name,
            "npwp_masked": taxpayer.npwp_masked,
            "ownership_pct": float(rel.ownership_pct) if rel.ownership_pct else None
        })

        # Get group for this taxpayer
        membership = (
            db.query(GroupMembership)
            .filter(GroupMembership.taxpayer_id == taxpayer.id)
            .first()
        )
        if membership:
            group_ids_seen.add(membership.group_id)

    # Get unique groups
    groups_data = []
    if group_ids_seen:
        from app.db.models import Group
        groups = db.query(Group).filter(Group.id.in_(group_ids_seen)).all()
        groups_data = [
            {
                "id": g.id,
                "name": g.name,
                "sector": g.sector
            }
            for g in groups
        ]

    return BODetailResponse(
        id=bo.id,
        name=bo.name,
        id_number_masked=bo.id_number_masked,
        nationality=bo.nationality,
        notes=bo.notes,
        taxpayers=taxpayers_data,
        groups=groups_data
    )
