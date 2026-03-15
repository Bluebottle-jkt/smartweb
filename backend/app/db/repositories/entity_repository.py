"""
EntityRepository – unified search across all entity types.

All /entities/suggest calls should go through this class so the
data-access strategy (search_index vs direct ORM queries) can be
changed without touching API code.
"""
from __future__ import annotations

import re
import unicodedata
from typing import List, Optional

from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.db.models import BeneficialOwner, Group, Officer, Taxpayer
from app.db.models.search_index import EntitySearchIndex
from app.db.repositories.base import BaseRepository


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s.lower()).strip()


class EntityRepository(BaseRepository[EntitySearchIndex]):
    def __init__(self, db: Session):
        super().__init__(EntitySearchIndex, db)

    # ------------------------------------------------------------------
    # Primary autocomplete – uses entity_search_index when populated,
    # falls back to direct ORM queries otherwise.
    # ------------------------------------------------------------------

    def suggest(
        self,
        q: str,
        limit: int = 8,
        entity_types: Optional[List[str]] = None,
    ) -> List[EntitySearchIndex]:
        """
        Returns up to `limit` EntitySearchIndex rows ranked by relevance.
        Falls back to direct ORM queries if index is empty.
        """
        if not q or len(q) < 2:
            return []

        # Check if index is populated
        try:
            index_count = self.db.query(EntitySearchIndex).limit(1).count()
        except Exception:
            index_count = 0

        if index_count > 0:
            return self._suggest_from_index(q, limit, entity_types)
        return self._suggest_from_orm(q, limit, entity_types)

    def _suggest_from_index(
        self, q: str, limit: int, entity_types: Optional[List[str]]
    ) -> List[EntitySearchIndex]:
        norm = _normalize(q)
        pattern = f"%{q}%"
        norm_pattern = f"%{norm}%"

        qry = self.db.query(EntitySearchIndex).filter(
            or_(
                EntitySearchIndex.name.ilike(pattern),
                EntitySearchIndex.normalized_name.ilike(norm_pattern),
                EntitySearchIndex.npwp.ilike(pattern),
            )
        )
        if entity_types:
            qry = qry.filter(EntitySearchIndex.entity_type.in_(entity_types))

        qry = qry.order_by(EntitySearchIndex.rank_score.desc())
        return qry.limit(limit).all()

    def _suggest_from_orm(
        self, q: str, limit: int, entity_types: Optional[List[str]]
    ) -> List[EntitySearchIndex]:
        """
        Fallback: query ORM tables directly and synthesise EntitySearchIndex-
        compatible objects (not persisted).
        """
        pattern = f"%{q}%"
        results: List[EntitySearchIndex] = []
        types = set(entity_types or ["TAXPAYER", "BENEFICIAL_OWNER", "GROUP", "OFFICER"])

        if "TAXPAYER" in types:
            try:
                sim = func.similarity(Taxpayer.name, q)
                tps = (
                    self.db.query(Taxpayer)
                    .filter(or_(Taxpayer.name.ilike(pattern), sim > 0.15))
                    .order_by(sim.desc())
                    .limit(limit)
                    .all()
                )
                for tp in tps:
                    row = EntitySearchIndex(
                        entity_type="TAXPAYER",
                        entity_id=tp.id,
                        name=tp.name,
                        npwp=getattr(tp, "npwp_masked", None),
                        entity_subtype=getattr(tp, "entity_type", None),
                        status=getattr(tp, "status", None),
                        rank_score=1.0,
                    )
                    results.append(row)
            except Exception:
                pass

        if "BENEFICIAL_OWNER" in types:
            try:
                sim = func.similarity(BeneficialOwner.name, q)
                bos = (
                    self.db.query(BeneficialOwner)
                    .filter(or_(BeneficialOwner.name.ilike(pattern), sim > 0.15))
                    .order_by(sim.desc())
                    .limit(limit)
                    .all()
                )
                for bo in bos:
                    row = EntitySearchIndex(
                        entity_type="BENEFICIAL_OWNER",
                        entity_id=bo.id,
                        name=bo.name,
                        nationality=getattr(bo, "nationality", None),
                        rank_score=0.8,
                    )
                    results.append(row)
            except Exception:
                pass

        if "GROUP" in types:
            try:
                sim = func.similarity(Group.name, q)
                groups = (
                    self.db.query(Group)
                    .filter(or_(Group.name.ilike(pattern), sim > 0.15))
                    .order_by(sim.desc())
                    .limit(limit)
                    .all()
                )
                for g in groups:
                    row = EntitySearchIndex(
                        entity_type="GROUP",
                        entity_id=g.id,
                        name=g.name,
                        rank_score=0.75,
                    )
                    results.append(row)
            except Exception:
                pass

        if "OFFICER" in types:
            try:
                sim = func.similarity(Officer.name, q)
                officers = (
                    self.db.query(Officer)
                    .filter(or_(Officer.name.ilike(pattern), sim > 0.15))
                    .order_by(sim.desc())
                    .limit(min(limit, 3))
                    .all()
                )
                for o in officers:
                    row = EntitySearchIndex(
                        entity_type="OFFICER",
                        entity_id=o.id,
                        name=o.name,
                        entity_subtype=getattr(o, "position", None),
                        rank_score=0.7,
                    )
                    results.append(row)
            except Exception:
                pass

        results.sort(key=lambda r: r.rank_score or 0, reverse=True)
        return results[:limit]

    # ------------------------------------------------------------------
    # Direct lookups
    # ------------------------------------------------------------------

    def get_by_npwp(self, npwp: str) -> Optional[EntitySearchIndex]:
        clean = re.sub(r"[.\-]", "", npwp)
        return (
            self.db.query(EntitySearchIndex)
            .filter(EntitySearchIndex.npwp.ilike(f"%{clean}%"))
            .first()
        )
