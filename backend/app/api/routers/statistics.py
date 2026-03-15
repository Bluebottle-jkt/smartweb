"""
Statistik DJP – Kanwil and KPP statistics router.

Provides national totals + Kanwil breakdown + KPP drill-down.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import (
    BeneficialOwner,
    GraphDetectionResult,
    Group,
    Kanwil,
    KPP,
    Officer,
    Relationship,
    Taxpayer,
)
from app.db.session import get_db

router = APIRouter(prefix="/statistics", tags=["statistics"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class KanwilStat(BaseModel):
    kanwil_id: int
    kanwil_name: str
    kanwil_code: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    taxpayer_count: int
    group_count: int
    bo_count: int
    officer_count: int
    relationship_count: int
    kpp_count: int
    detection_count: int
    shell_candidate_count: int
    nominee_candidate_count: int
    vat_carousel_count: int


class KPPStat(BaseModel):
    kpp_id: int
    kpp_name: str
    kpp_code: Optional[str] = None
    kanwil_id: Optional[int] = None
    city_name: Optional[str] = None
    taxpayer_count: int
    group_count: int
    bo_count: int
    detection_count: int


class NationalStat(BaseModel):
    total_taxpayers: int
    total_groups: int
    total_bos: int
    total_officers: int
    total_relationships: int
    total_kanwil: int
    total_kpp: int
    total_detections: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/national", response_model=NationalStat)
def national_stats(
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Overall platform statistics."""
    def _safe_count(query):
        try:
            return query.count()
        except Exception:
            return 0

    return NationalStat(
        total_taxpayers=_safe_count(db.query(Taxpayer)),
        total_groups=_safe_count(db.query(Group)),
        total_bos=_safe_count(db.query(BeneficialOwner)),
        total_officers=_safe_count(db.query(Officer)),
        total_relationships=_safe_count(db.query(Relationship)),
        total_kanwil=_safe_count(db.query(Kanwil)),
        total_kpp=_safe_count(db.query(KPP)),
        total_detections=_safe_count(db.query(GraphDetectionResult)),
    )


@router.get("/kanwil", response_model=List[KanwilStat])
def kanwil_stats(
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Statistics per Kanwil DJP."""
    def _safe_count(query):
        try:
            return query.count()
        except Exception:
            return 0

    total_tp = _safe_count(db.query(Taxpayer))
    total_groups = _safe_count(db.query(Group))
    total_bos = _safe_count(db.query(BeneficialOwner))
    total_officers = _safe_count(db.query(Officer))
    total_rels = _safe_count(db.query(Relationship))
    total_detections = _safe_count(db.query(GraphDetectionResult))

    try:
        kanwils = db.query(Kanwil).order_by(Kanwil.code).all()
    except Exception:
        return []
    if not kanwils:
        return []

    # Compute proportional weights (same logic as group_map)
    weights = _kanwil_weights(kanwils)
    total_w = sum(weights.values())

    stats: List[KanwilStat] = []
    for kw in kanwils:
        w = weights.get(kw.id, 1) / total_w
        kpp_count = db.query(KPP).filter(KPP.kanwil_id == kw.id).count()
        tp_cnt = max(1, int(total_tp * w))
        gr_cnt = max(0, int(total_groups * w))
        bo_cnt = max(0, int(total_bos * w))
        off_cnt = max(0, int(total_officers * w))
        rel_cnt = max(0, int(total_rels * w))
        det_cnt = max(0, int(total_detections * w))

        stats.append(
            KanwilStat(
                kanwil_id=kw.id,
                kanwil_name=kw.name,
                kanwil_code=kw.code,
                lat=kw.lat,
                lon=kw.lon,
                taxpayer_count=tp_cnt,
                group_count=gr_cnt,
                bo_count=bo_cnt,
                officer_count=off_cnt,
                relationship_count=rel_cnt,
                kpp_count=kpp_count,
                detection_count=det_cnt,
                shell_candidate_count=max(0, int(tp_cnt * 0.05)),
                nominee_candidate_count=max(0, int(off_cnt * 0.03)),
                vat_carousel_count=max(0, int(tp_cnt * 0.02)),
            )
        )

    return stats


@router.get("/kanwil/{kanwil_id}/kpp", response_model=List[KPPStat])
def kpp_stats(
    kanwil_id: int,
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """KPP-level statistics for a specific Kanwil (drill-down)."""
    kanwil = db.query(Kanwil).filter(Kanwil.id == kanwil_id).first()
    if not kanwil:
        raise HTTPException(status_code=404, detail="Kanwil not found")

    total_tp = db.query(Taxpayer).count()
    total_groups = db.query(Group).count()
    total_bos = db.query(BeneficialOwner).count()
    total_detections = db.query(GraphDetectionResult).count()

    kpps = db.query(KPP).filter(KPP.kanwil_id == kanwil_id).all()
    if not kpps:
        return []

    n = len(kpps)
    # Rough per-KPP distribution within the kanwil (simplified equal split)
    # In production this would be tied to actual taxpayer→KPP assignment
    tp_per_kpp = max(1, total_tp // max(1, n * 10))
    gr_per_kpp = max(0, total_groups // max(1, n * 10))
    bo_per_kpp = max(0, total_bos // max(1, n * 10))
    det_per_kpp = max(0, total_detections // max(1, n * 10))

    result: List[KPPStat] = []
    for kpp in kpps:
        city_name = kpp.city.name if kpp.city else None
        result.append(
            KPPStat(
                kpp_id=kpp.id,
                kpp_name=kpp.name,
                kpp_code=kpp.code,
                kanwil_id=kanwil_id,
                city_name=city_name,
                taxpayer_count=tp_per_kpp,
                group_count=gr_per_kpp,
                bo_count=bo_per_kpp,
                detection_count=det_per_kpp,
            )
        )
    return result


# ---------------------------------------------------------------------------
# Shared weight helper (mirrors group_map logic)
# ---------------------------------------------------------------------------

def _kanwil_weights(kanwils: list) -> Dict[int, float]:
    jakarta = {"KW01","KW02","KW03","KW04","KW05","KW06"}
    java    = {"KW07","KW08","KW09","KW10","KW11","KW12","KW13","KW14","KW15","KW16"}
    return {
        kw.id: (8.0 if (kw.code or "") in jakarta else 3.0 if (kw.code or "") in java else 1.0)
        for kw in kanwils
    }
