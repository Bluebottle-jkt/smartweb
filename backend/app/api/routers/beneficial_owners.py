from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.api.deps import get_current_user
from app.db.models import BeneficialOwner, BeneficialOwnerTaxpayer, GroupMembership

router = APIRouter(prefix="/beneficial-owners", tags=["beneficial_owners"])


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
