from typing import List, Dict, Any, Optional
from sqlalchemy import or_, func, case, literal_column
from sqlalchemy.orm import Session

from app.db.models import Group, Taxpayer, BeneficialOwner


class SearchService:
    """Service for fast keyword search with pg_trgm similarity."""

    @staticmethod
    def suggest(db: Session, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fast typeahead search across Groups, Taxpayers, and Beneficial Owners.
        Uses pg_trgm similarity and ILIKE for partial matching.
        """
        if not query or len(query) < 2:
            return []

        query_pattern = f"%{query}%"
        results = []

        # Search Groups
        group_similarity = func.similarity(Group.name, query)
        group_exact_prefix = case(
            (Group.name.ilike(f"{query}%"), 3),
            (Group.name.ilike(query_pattern), 2),
            else_=1
        )

        groups = (
            db.query(
                Group.id,
                Group.name,
                Group.sector,
                literal_column("'GROUP'").label("entity_type"),
                (group_exact_prefix + group_similarity).label("rank")
            )
            .filter(
                or_(
                    Group.name.ilike(query_pattern),
                    group_similarity > 0.2
                )
            )
            .order_by(literal_column("rank").desc())
            .limit(limit)
            .all()
        )

        for g in groups:
            results.append({
                "entity_type": "GROUP",
                "id": g.id,
                "name": g.name,
                "subtitle": g.sector or "Grup",
                "rank": float(g.rank)
            })

        # Search Taxpayers
        taxpayer_similarity = func.similarity(Taxpayer.name, query)
        taxpayer_exact_prefix = case(
            (Taxpayer.name.ilike(f"{query}%"), 3),
            (Taxpayer.name.ilike(query_pattern), 2),
            else_=1
        )

        taxpayers = (
            db.query(
                Taxpayer.id,
                Taxpayer.name,
                Taxpayer.npwp_masked,
                Taxpayer.entity_type,
                literal_column("'TAXPAYER'").label("entity_type_label"),
                (taxpayer_exact_prefix + taxpayer_similarity).label("rank")
            )
            .filter(
                or_(
                    Taxpayer.name.ilike(query_pattern),
                    taxpayer_similarity > 0.2
                )
            )
            .order_by(literal_column("rank").desc())
            .limit(limit)
            .all()
        )

        for t in taxpayers:
            results.append({
                "entity_type": "TAXPAYER",
                "id": t.id,
                "name": t.name,
                "subtitle": t.npwp_masked,
                "rank": float(t.rank)
            })

        # Search Beneficial Owners
        bo_similarity = func.similarity(BeneficialOwner.name, query)
        bo_exact_prefix = case(
            (BeneficialOwner.name.ilike(f"{query}%"), 3),
            (BeneficialOwner.name.ilike(query_pattern), 2),
            else_=1
        )

        bos = (
            db.query(
                BeneficialOwner.id,
                BeneficialOwner.name,
                BeneficialOwner.nationality,
                literal_column("'BENEFICIAL_OWNER'").label("entity_type"),
                (bo_exact_prefix + bo_similarity).label("rank")
            )
            .filter(
                or_(
                    BeneficialOwner.name.ilike(query_pattern),
                    bo_similarity > 0.2
                )
            )
            .order_by(literal_column("rank").desc())
            .limit(limit)
            .all()
        )

        for b in bos:
            results.append({
                "entity_type": "BENEFICIAL_OWNER",
                "id": b.id,
                "name": b.name,
                "subtitle": b.nationality or "Beneficial Owner",
                "rank": float(b.rank)
            })

        # Sort all results by rank and return top N
        results.sort(key=lambda x: x["rank"], reverse=True)
        return results[:limit]

    @staticmethod
    def search_with_filters(
        db: Session,
        query: Optional[str] = None,
        entity_type: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        risk_level: Optional[str] = None,
        sector: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Full search with pagination and filters.
        """
        results = []
        total = 0

        if entity_type == "GROUP" or entity_type is None:
            # Search groups
            group_query = db.query(Group)

            if query:
                query_pattern = f"%{query}%"
                group_query = group_query.filter(Group.name.ilike(query_pattern))

            if sector:
                group_query = group_query.filter(Group.sector == sector)

            if entity_type == "GROUP":
                total = group_query.count()
                groups = group_query.offset((page - 1) * page_size).limit(page_size).all()

                for g in groups:
                    results.append({
                        "entity_type": "GROUP",
                        "id": g.id,
                        "name": g.name,
                        "sector": g.sector,
                        "created_at": g.created_at.isoformat() if g.created_at else None
                    })

        if entity_type == "TAXPAYER" or entity_type is None:
            # Search taxpayers
            taxpayer_query = db.query(Taxpayer)

            if query:
                query_pattern = f"%{query}%"
                taxpayer_query = taxpayer_query.filter(Taxpayer.name.ilike(query_pattern))

            if entity_type == "TAXPAYER":
                total = taxpayer_query.count()
                taxpayers = taxpayer_query.offset((page - 1) * page_size).limit(page_size).all()

                for t in taxpayers:
                    results.append({
                        "entity_type": "TAXPAYER",
                        "id": t.id,
                        "name": t.name,
                        "npwp_masked": t.npwp_masked,
                        "entity_type_label": t.entity_type,
                        "status": t.status
                    })

        if entity_type == "BENEFICIAL_OWNER" or entity_type is None:
            # Search beneficial owners
            bo_query = db.query(BeneficialOwner)

            if query:
                query_pattern = f"%{query}%"
                bo_query = bo_query.filter(BeneficialOwner.name.ilike(query_pattern))

            if entity_type == "BENEFICIAL_OWNER":
                total = bo_query.count()
                bos = bo_query.offset((page - 1) * page_size).limit(page_size).all()

                for b in bos:
                    results.append({
                        "entity_type": "BENEFICIAL_OWNER",
                        "id": b.id,
                        "name": b.name,
                        "nationality": b.nationality
                    })

        if entity_type is None and not results:
            # Mixed search - limit results per type
            total = 0  # Mixed mode doesn't have accurate total

        return {
            "results": results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 1
        }
