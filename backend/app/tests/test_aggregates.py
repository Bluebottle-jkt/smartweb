import pytest
from sqlalchemy.orm import Session
from app.services.aggregate_service import AggregateService


def test_get_group_aggregates(db: Session):
    """Test getting group aggregates."""
    # Assumes group with ID 1 exists in test database
    result = AggregateService.get_group_aggregates(db, 1)

    assert "group_id" in result
    assert "member_count" in result
    assert "yearly_aggregates" in result
    assert "risk_summary" in result


def test_get_group_aggregates_empty_group(db: Session):
    """Test getting aggregates for non-existent group."""
    result = AggregateService.get_group_aggregates(db, 99999)

    assert result["member_count"] == 0
    assert result["yearly_aggregates"] == []
