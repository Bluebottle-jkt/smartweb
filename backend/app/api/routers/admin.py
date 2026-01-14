from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import date

from app.db.session import get_db, SessionLocal, engine
from app.api.deps import get_current_active_admin
from app.core.config import settings
from app.db.seed import generate_seed_data, reset_database
from app.db.models import Group
from app.services.group_derivation_service import GroupDerivationService

router = APIRouter(prefix="/admin", tags=["admin"])


class DeriveGroupsRequest(BaseModel):
    as_of_date: Optional[str] = None
    rule_set_id: Optional[int] = None


@router.post("/seed/reset-and-generate")
def reset_and_seed(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """
    Dangerously reset database and regenerate seed data.
    Requires Admin role and ALLOW_DB_RESET=true.
    """
    if not settings.ALLOW_DB_RESET:
        raise HTTPException(
            status_code=403,
            detail="Database reset not allowed. Set ALLOW_DB_RESET=true in environment."
        )

    try:
        # Reset database
        reset_database(engine)

        # Run migrations
        import os
        result = os.system("cd backend && alembic upgrade head")
        if result != 0:
            raise RuntimeError("Migration failed")

        # Generate seed data
        fresh_db = SessionLocal()
        try:
            generate_seed_data(fresh_db)
        finally:
            fresh_db.close()

        return {
            "message": "Database reset and seed data generated successfully",
            "groups": settings.SEED_GROUPS,
            "taxpayers": settings.SEED_TAXPAYERS,
            "beneficial_owners": settings.SEED_BOS
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


@router.get("/stats")
def get_system_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """Get system statistics."""
    from app.db.models import Taxpayer, BeneficialOwner, Relationship, DerivedGroup

    group_count = db.query(Group).count()
    taxpayer_count = db.query(Taxpayer).count()
    bo_count = db.query(BeneficialOwner).count()
    relationship_count = db.query(Relationship).count()
    derived_group_count = db.query(DerivedGroup).count()

    return {
        "groups": group_count,
        "taxpayers": taxpayer_count,
        "beneficial_owners": bo_count,
        "relationships": relationship_count,
        "derived_groups": derived_group_count
    }


@router.post("/derive-groups")
def derive_groups(
    request: DeriveGroupsRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """
    Derive groups from relationship graph based on active rule set.
    Requires Admin role and ALLOW_DERIVE=true.
    """
    if not settings.ALLOW_DERIVE:
        raise HTTPException(
            status_code=403,
            detail="Group derivation not allowed. Set ALLOW_DERIVE=true in environment."
        )

    try:
        # Parse as_of_date if provided
        as_of_date_obj = None
        if request.as_of_date:
            from datetime import datetime
            as_of_date_obj = datetime.strptime(request.as_of_date, "%Y-%m-%d").date()

        # Run derivation
        summary = GroupDerivationService.derive_groups(
            db=db,
            rule_set_id=request.rule_set_id,
            as_of_date=as_of_date_obj
        )

        return {
            "message": "Derived groups generated successfully",
            "summary": summary
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Derivation failed: {str(e)}")
