"""
StatisticsRepository – aggregation queries for dashboard statistics.

Decouples API routers from direct ORM queries so schema changes only
require updating this layer.
"""
from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from app.db.models import (
    BeneficialOwner, Group, Officer, Relationship, Taxpayer
)
from app.db.models.graph_intelligence import GraphDetectionResult


class StatisticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def _safe_count(self, query) -> int:
        try:
            return query.count()
        except Exception:
            return 0

    def national_totals(self) -> Dict[str, int]:
        return {
            "total_taxpayers":   self._safe_count(self.db.query(Taxpayer)),
            "total_groups":      self._safe_count(self.db.query(Group)),
            "total_bos":         self._safe_count(self.db.query(BeneficialOwner)),
            "total_officers":    self._safe_count(self.db.query(Officer)),
            "total_relationships": self._safe_count(self.db.query(Relationship)),
            "total_detections":  self._safe_count(self.db.query(GraphDetectionResult)),
        }

    def kanwil_counts(self) -> Dict[str, int]:
        """
        Returns kanwil / kpp counts without importing geography models
        at import time (avoids circular imports).
        """
        try:
            from app.db.models.geography import Kanwil, KPP
            return {
                "total_kanwil": self._safe_count(self.db.query(Kanwil)),
                "total_kpp":    self._safe_count(self.db.query(KPP)),
            }
        except Exception:
            return {"total_kanwil": 0, "total_kpp": 0}
