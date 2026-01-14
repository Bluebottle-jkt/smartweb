from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/suggest")
def search_suggest(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Fast typeahead search suggestions."""
    return SearchService.suggest(db, q, limit)


@router.get("")
def search(
    q: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    risk_level: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Full search with filters and pagination."""
    return SearchService.search_with_filters(
        db, q, entity_type, year_from, year_to, risk_level, sector, page, page_size
    )
