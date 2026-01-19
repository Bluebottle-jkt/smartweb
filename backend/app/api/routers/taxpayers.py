from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.api.deps import get_current_user
from app.db.models import (
    Taxpayer, GroupMembership, BeneficialOwnerTaxpayer,
    TaxpayerYearlyFinancial, TaxpayerYearlyRatio,
    TaxpayerYearlyAffiliateTx, TaxpayerTreatmentHistory,
    TaxpayerRisk
)

router = APIRouter(prefix="/taxpayers", tags=["taxpayers"])


class TaxpayerListItem(BaseModel):
    id: int
    npwp_masked: str
    name: str
    entity_type: Optional[str]
    address: Optional[str]
    status: Optional[str]

    class Config:
        from_attributes = True


class TaxpayerListResponse(BaseModel):
    items: List[TaxpayerListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class TaxpayerDetailResponse(BaseModel):
    id: int
    npwp_masked: str
    name: str
    entity_type: Optional[str]
    address: Optional[str]
    status: Optional[str]
    group: Optional[dict]
    beneficial_owners: List[dict]
    yearly_financials: List[dict]
    yearly_ratios: List[dict]
    yearly_affiliate_txs: List[dict]
    treatment_histories: List[dict]
    risks: List[dict]

    class Config:
        from_attributes = True


@router.get("", response_model=TaxpayerListResponse)
def list_taxpayers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List taxpayers with pagination and filtering."""
    query = db.query(Taxpayer)

    # Apply filters
    if search:
        query = query.filter(
            (Taxpayer.name.ilike(f"%{search}%")) |
            (Taxpayer.npwp_masked.ilike(f"%{search}%"))
        )

    if entity_type:
        query = query.filter(Taxpayer.entity_type == entity_type)

    if status:
        query = query.filter(Taxpayer.status == status)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    items = query.order_by(Taxpayer.name).offset(offset).limit(page_size).all()

    total_pages = (total + page_size - 1) // page_size

    return TaxpayerListResponse(
        items=[TaxpayerListItem.from_orm(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{taxpayer_id}")
def get_taxpayer(
    taxpayer_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get taxpayer detail with all related data."""
    taxpayer = db.query(Taxpayer).filter(Taxpayer.id == taxpayer_id).first()
    if not taxpayer:
        raise HTTPException(status_code=404, detail="Taxpayer not found")

    # Get group membership
    membership = (
        db.query(GroupMembership)
        .filter(GroupMembership.taxpayer_id == taxpayer_id)
        .first()
    )

    group_data = None
    if membership:
        group_data = {
            "id": membership.group.id,
            "name": membership.group.name,
            "role": membership.role
        }

    # Get beneficial owners
    bo_relationships = (
        db.query(BeneficialOwnerTaxpayer)
        .filter(BeneficialOwnerTaxpayer.taxpayer_id == taxpayer_id)
        .all()
    )

    bos = [
        {
            "id": rel.beneficial_owner.id,
            "name": rel.beneficial_owner.name,
            "ownership_pct": float(rel.ownership_pct) if rel.ownership_pct else None
        }
        for rel in bo_relationships
    ]

    # Get yearly financials
    financials = db.query(TaxpayerYearlyFinancial).filter(
        TaxpayerYearlyFinancial.taxpayer_id == taxpayer_id
    ).order_by(TaxpayerYearlyFinancial.tax_year).all()

    financials_data = [
        {
            "tax_year": f.tax_year,
            "turnover": float(f.turnover) if f.turnover else None,
            "loss_compensation": float(f.loss_compensation) if f.loss_compensation else None,
            "spt_status": f.spt_status
        }
        for f in financials
    ]

    # Get yearly ratios
    ratios = db.query(TaxpayerYearlyRatio).filter(
        TaxpayerYearlyRatio.taxpayer_id == taxpayer_id
    ).order_by(TaxpayerYearlyRatio.tax_year, TaxpayerYearlyRatio.ratio_code).all()

    ratios_data = [
        {
            "tax_year": r.tax_year,
            "ratio_code": r.ratio_code,
            "ratio_value": float(r.ratio_value) if r.ratio_value else None
        }
        for r in ratios
    ]

    # Get affiliate transactions
    affiliate_txs = db.query(TaxpayerYearlyAffiliateTx).filter(
        TaxpayerYearlyAffiliateTx.taxpayer_id == taxpayer_id
    ).order_by(TaxpayerYearlyAffiliateTx.tax_year).all()

    affiliate_data = [
        {
            "tax_year": tx.tax_year,
            "direction": tx.direction.value,
            "tx_type": tx.tx_type,
            "tx_value": float(tx.tx_value) if tx.tx_value else None
        }
        for tx in affiliate_txs
    ]

    # Get treatment histories
    treatments = db.query(TaxpayerTreatmentHistory).filter(
        TaxpayerTreatmentHistory.taxpayer_id == taxpayer_id
    ).order_by(TaxpayerTreatmentHistory.treatment_date.desc()).all()

    treatment_data = [
        {
            "id": t.id,
            "treatment_date": t.treatment_date.isoformat(),
            "treatment_type": t.treatment_type,
            "notes": t.notes,
            "outcome": t.outcome
        }
        for t in treatments
    ]

    # Get risks
    risks = db.query(TaxpayerRisk).filter(
        TaxpayerRisk.taxpayer_id == taxpayer_id
    ).all()

    risk_data = [
        {
            "id": r.id,
            "tax_year": r.tax_year,
            "risk_source": r.risk_source.value,
            "risk_level": r.risk_level.value if r.risk_level else None,
            "risk_score": float(r.risk_score) if r.risk_score else None,
            "notes": r.notes
        }
        for r in risks
    ]

    return TaxpayerDetailResponse(
        id=taxpayer.id,
        npwp_masked=taxpayer.npwp_masked,
        name=taxpayer.name,
        entity_type=taxpayer.entity_type,
        address=taxpayer.address,
        status=taxpayer.status,
        group=group_data,
        beneficial_owners=bos,
        yearly_financials=financials_data,
        yearly_ratios=ratios_data,
        yearly_affiliate_txs=affiliate_data,
        treatment_histories=treatment_data,
        risks=risk_data
    )
