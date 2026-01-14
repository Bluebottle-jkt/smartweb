from typing import Dict, Any, List
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    Group, Taxpayer, GroupMembership,
    TaxpayerYearlyFinancial, TaxpayerYearlyAffiliateTx,
    TaxpayerRisk, RiskSource
)


class AggregateService:
    """Service for calculating aggregated group metrics."""

    @staticmethod
    def get_group_aggregates(db: Session, group_id: int) -> Dict[str, Any]:
        """
        Calculate aggregated metrics for a group across all members.
        """
        # Get all taxpayer IDs in the group
        member_ids = [
            m.taxpayer_id for m in
            db.query(GroupMembership.taxpayer_id)
            .filter(GroupMembership.group_id == group_id)
            .all()
        ]

        if not member_ids:
            return {
                "group_id": group_id,
                "member_count": 0,
                "yearly_aggregates": []
            }

        # Aggregate turnover by year
        yearly_financials = (
            db.query(
                TaxpayerYearlyFinancial.tax_year,
                func.sum(TaxpayerYearlyFinancial.turnover).label("total_turnover"),
                func.sum(TaxpayerYearlyFinancial.loss_compensation).label("total_loss_compensation"),
                func.count(TaxpayerYearlyFinancial.id).label("record_count")
            )
            .filter(TaxpayerYearlyFinancial.taxpayer_id.in_(member_ids))
            .group_by(TaxpayerYearlyFinancial.tax_year)
            .order_by(TaxpayerYearlyFinancial.tax_year)
            .all()
        )

        # Aggregate affiliate transactions by year
        yearly_affiliates = (
            db.query(
                TaxpayerYearlyAffiliateTx.tax_year,
                TaxpayerYearlyAffiliateTx.direction,
                func.sum(TaxpayerYearlyAffiliateTx.tx_value).label("total_value")
            )
            .filter(TaxpayerYearlyAffiliateTx.taxpayer_id.in_(member_ids))
            .group_by(TaxpayerYearlyAffiliateTx.tax_year, TaxpayerYearlyAffiliateTx.direction)
            .all()
        )

        # Organize affiliate data by year
        affiliate_by_year = {}
        for aff in yearly_affiliates:
            year = aff.tax_year
            if year not in affiliate_by_year:
                affiliate_by_year[year] = {"domestic": 0, "foreign": 0}
            affiliate_by_year[year][aff.direction.value] = float(aff.total_value or 0)

        # Build yearly aggregates
        yearly_agg = []
        for fin in yearly_financials:
            year_data = {
                "year": fin.tax_year,
                "total_turnover": float(fin.total_turnover or 0),
                "total_loss_compensation": float(fin.total_loss_compensation or 0),
                "member_count": fin.record_count,
                "affiliate_domestic": affiliate_by_year.get(fin.tax_year, {}).get("domestic", 0),
                "affiliate_foreign": affiliate_by_year.get(fin.tax_year, {}).get("foreign", 0)
            }
            yearly_agg.append(year_data)

        # Get risk summary
        risk_summary = AggregateService._get_group_risk_summary(db, member_ids)

        return {
            "group_id": group_id,
            "member_count": len(member_ids),
            "yearly_aggregates": yearly_agg,
            "risk_summary": risk_summary
        }

    @staticmethod
    def _get_group_risk_summary(db: Session, member_ids: List[int]) -> Dict[str, Any]:
        """Get risk summary for group members."""
        # Count members by CRM risk level
        crm_risk_counts = (
            db.query(
                TaxpayerRisk.risk_level,
                func.count(func.distinct(TaxpayerRisk.taxpayer_id)).label("count")
            )
            .filter(
                TaxpayerRisk.taxpayer_id.in_(member_ids),
                TaxpayerRisk.risk_source == RiskSource.CRM,
                TaxpayerRisk.risk_level.isnot(None)
            )
            .group_by(TaxpayerRisk.risk_level)
            .all()
        )

        risk_dist = {level.value: 0 for level in TaxpayerRisk.__table__.c.risk_level.type.enum_class}
        for risk in crm_risk_counts:
            if risk.risk_level:
                risk_dist[risk.risk_level.value] = risk.count

        # Get average GroupEngine score
        avg_group_score = (
            db.query(func.avg(TaxpayerRisk.risk_score))
            .filter(
                TaxpayerRisk.taxpayer_id.in_(member_ids),
                TaxpayerRisk.risk_source == RiskSource.GROUP_ENGINE,
                TaxpayerRisk.risk_score.isnot(None)
            )
            .scalar()
        )

        return {
            "crm_risk_distribution": risk_dist,
            "avg_group_engine_score": float(avg_group_score) if avg_group_score else None
        }
