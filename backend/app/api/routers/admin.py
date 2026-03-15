from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
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


# ─────────────────────────────────────────────────────────────────────────────
# ETL / Ingestion endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/ingest/csv")
async def ingest_csv_file(
    dataset_key: str = Form(..., description="Dataset key from schema_mapping.yaml, e.g. 'taxpayers'"),
    delimiter: str = Form(default=";", description="CSV delimiter character"),
    encoding: str = Form(default="utf-8-sig"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_admin),
):
    """
    Upload a CSV file and ingest it according to the schema_mapping.yaml configuration.
    Only Admin users can perform ingestion.
    """
    from app.services.ingestion_service import IngestionService

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:  # 50 MB guard
        raise HTTPException(status_code=413, detail="File too large (max 50 MB).")

    service = IngestionService(db)
    try:
        version = service.ingest_csv(
            content=content,
            dataset_key=dataset_key,
            filename=file.filename or "upload.csv",
            ingested_by=current_user.username,
            delimiter=delimiter,
            encoding=encoding,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

    return {
        "version_tag": version.version_tag,
        "status": version.status,
        "record_count": version.record_count,
        "entity_count": version.entity_count,
        "message": f"Ingested {version.record_count} records into '{dataset_key}'.",
    }


@router.get("/ingest/versions")
def list_ingestion_versions(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_admin),
):
    """List recent ingestion/dataset version history."""
    from app.services.ingestion_service import IngestionService

    service = IngestionService(db)
    versions = service.list_versions(limit=limit)
    return [
        {
            "id": v.id,
            "version_tag": v.version_tag,
            "source_file": v.source_file,
            "source_type": v.source_type,
            "status": v.status,
            "record_count": v.record_count,
            "entity_count": v.entity_count,
            "ingested_by": v.ingested_by,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "error_message": v.error_message,
        }
        for v in versions
    ]


@router.get("/ingest/schema")
def get_ingestion_schema(
    current_user=Depends(get_current_active_admin),
):
    """Return available dataset mappings from schema_mapping.yaml."""
    from app.services.ingestion_service import IngestionService
    from app.db.session import get_db as _gdb

    db = next(_gdb())
    try:
        service = IngestionService(db)
        return service.get_config_summary()
    finally:
        db.close()


@router.post("/ingest/rebuild-search-index")
def rebuild_search_index(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_admin),
):
    """Rebuild the entity_search_index from all live ORM tables."""
    from app.db.search_index import refresh_entity_search_index

    try:
        counts = refresh_entity_search_index(db)
        return {"status": "ok", "indexed": counts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
