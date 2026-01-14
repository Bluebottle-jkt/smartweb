import pytest
from sqlalchemy.orm import Session
from app.services.search_service import SearchService
from app.db.models import Group, Taxpayer, BeneficialOwner


def test_search_suggest_groups(db: Session):
    """Test search suggest for groups."""
    # This test requires a populated database
    # In real scenario, you'd set up test fixtures
    results = SearchService.suggest(db, "grab", limit=10)
    assert isinstance(results, list)
    # Results should contain entities with "grab" in name


def test_search_suggest_min_length(db: Session):
    """Test that search requires minimum 2 characters."""
    results = SearchService.suggest(db, "a", limit=10)
    assert len(results) == 0


def test_search_with_filters(db: Session):
    """Test search with filters."""
    results = SearchService.search_with_filters(
        db,
        query="test",
        entity_type="GROUP",
        page=1,
        page_size=20
    )
    assert "results" in results
    assert "total" in results
    assert "page" in results
