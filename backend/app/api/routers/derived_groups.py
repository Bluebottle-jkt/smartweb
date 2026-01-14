from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.api.deps import get_current_user
from app.db.models import DerivedGroup, DerivedGroupMembership, Relationship, EntityType

router = APIRouter(prefix="/derived-groups", tags=["derived_groups"])


class DerivedGroupResponse(BaseModel):
    id: int
    group_key: str
    rule_set_id: int
    generated_at: str
    as_of_date: Optional[str]
    summary: Optional[dict]
    member_count: int = 0

    class Config:
        from_attributes = True


class DerivedGroupDetailResponse(BaseModel):
    id: int
    group_key: str
    rule_set_id: int
    rule_set_name: str
    generated_at: str
    as_of_date: Optional[str]
    summary: Optional[dict]
    members: List[dict]

    class Config:
        from_attributes = True


@router.get("", response_model=List[DerivedGroupResponse])
def list_derived_groups(
    rule_set_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List derived groups with pagination."""
    query = db.query(DerivedGroup)

    if rule_set_id:
        query = query.filter(DerivedGroup.rule_set_id == rule_set_id)

    query = query.order_by(DerivedGroup.generated_at.desc())

    total = query.count()
    groups = query.offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for group in groups:
        member_count = db.query(DerivedGroupMembership).filter(
            DerivedGroupMembership.derived_group_id == group.id
        ).count()

        result.append(DerivedGroupResponse(
            id=group.id,
            group_key=group.group_key,
            rule_set_id=group.rule_set_id,
            generated_at=group.generated_at.isoformat(),
            as_of_date=group.as_of_date.isoformat() if group.as_of_date else None,
            summary=group.summary,
            member_count=member_count
        ))

    return result


@router.get("/{group_id}", response_model=DerivedGroupDetailResponse)
def get_derived_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get derived group detail with members."""
    group = db.query(DerivedGroup).filter(DerivedGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Derived group not found")

    # Get members
    memberships = db.query(DerivedGroupMembership).filter(
        DerivedGroupMembership.derived_group_id == group_id
    ).all()

    members = []
    for membership in memberships:
        taxpayer = membership.taxpayer
        members.append({
            "taxpayer_id": taxpayer.id,
            "name": taxpayer.name,
            "npwp_masked": taxpayer.npwp_masked,
            "strength_score": float(membership.strength_score) if membership.strength_score else None,
            "evidence_summary": {
                "total_connections": membership.evidence.get("total_connections", 0),
                "path_count": len(membership.evidence.get("paths", []))
            }
        })

    return DerivedGroupDetailResponse(
        id=group.id,
        group_key=group.group_key,
        rule_set_id=group.rule_set_id,
        rule_set_name=group.rule_set.name if group.rule_set else "Unknown",
        generated_at=group.generated_at.isoformat(),
        as_of_date=group.as_of_date.isoformat() if group.as_of_date else None,
        summary=group.summary,
        members=members
    )


@router.get("/taxpayers/{taxpayer_id}")
def get_taxpayer_derived_groups(
    taxpayer_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get derived groups for a specific taxpayer."""
    memberships = db.query(DerivedGroupMembership).filter(
        DerivedGroupMembership.taxpayer_id == taxpayer_id
    ).all()

    result = []
    for membership in memberships:
        group = membership.derived_group
        result.append({
            "derived_group_id": group.id,
            "group_key": group.group_key,
            "rule_set_name": group.rule_set.name if group.rule_set else "Unknown",
            "generated_at": group.generated_at.isoformat(),
            "strength_score": float(membership.strength_score) if membership.strength_score else None,
            "member_count": group.summary.get("size", 0) if group.summary else 0,
            "reason_snippet": _build_reason_snippet(membership.evidence)
        })

    return result


@router.get("/beneficial-owners/{bo_id}")
def get_bo_derived_groups(
    bo_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get derived groups related to a beneficial owner (via their taxpayers)."""
    # Find taxpayers owned by this BO
    from app.db.models import BeneficialOwnerTaxpayer

    bo_taxpayers = db.query(BeneficialOwnerTaxpayer).filter(
        BeneficialOwnerTaxpayer.beneficial_owner_id == bo_id
    ).all()

    taxpayer_ids = [rel.taxpayer_id for rel in bo_taxpayers]

    if not taxpayer_ids:
        return []

    # Find derived groups containing these taxpayers
    memberships = db.query(DerivedGroupMembership).filter(
        DerivedGroupMembership.taxpayer_id.in_(taxpayer_ids)
    ).all()

    # Deduplicate by derived_group_id
    groups_seen = set()
    result = []

    for membership in memberships:
        if membership.derived_group_id in groups_seen:
            continue

        groups_seen.add(membership.derived_group_id)
        group = membership.derived_group

        result.append({
            "derived_group_id": group.id,
            "group_key": group.group_key,
            "rule_set_name": group.rule_set.name if group.rule_set else "Unknown",
            "generated_at": group.generated_at.isoformat(),
            "member_count": group.summary.get("size", 0) if group.summary else 0,
            "related_via_taxpayer": membership.taxpayer.name
        })

    return result


def _build_reason_snippet(evidence: dict) -> str:
    """Build a human-readable reason snippet from evidence."""
    total_connections = evidence.get("total_connections", 0)
    path_count = len(evidence.get("paths", []))

    if total_connections > 0:
        return f"{total_connections} koneksi langsung, {path_count} jalur hubungan"
    return "Hubungan istimewa terdeteksi"
