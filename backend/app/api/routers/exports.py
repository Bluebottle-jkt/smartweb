from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.api.deps import get_current_user
from app.services.export_service import ExportService
from app.db.models import AuditLog

router = APIRouter(prefix="/exports", tags=["exports"])


class ExportRequest(BaseModel):
    taxpayer_ids: List[int]


@router.get("/groups/{group_id}/members")
def export_group_members(
    group_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Export group members to CSV."""
    try:
        csv_content = ExportService.export_group_members(db, group_id)

        # Log export action
        audit = AuditLog(
            actor_user_id=current_user.id,
            action="EXPORT",
            entity_type="Group",
            entity_id=group_id,
            payload={"export_type": "members"}
        )
        db.add(audit)
        db.commit()

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=group_{group_id}_members.csv"}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/search-results")
def export_search_results(
    request: ExportRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Export search results to CSV."""
    csv_content = ExportService.export_search_results(db, request.taxpayer_ids)

    # Log export action
    audit = AuditLog(
        actor_user_id=current_user.id,
        action="EXPORT",
        entity_type="SearchResults",
        payload={"count": len(request.taxpayer_ids)}
    )
    db.add(audit)
    db.commit()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=search_results.csv"}
    )
