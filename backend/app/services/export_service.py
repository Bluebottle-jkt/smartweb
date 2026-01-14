import io
import csv
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.db.models import (
    Group, Taxpayer, GroupMembership,
    TaxpayerYearlyFinancial, TaxpayerYearlyRatio,
    TaxpayerYearlyAffiliateTx
)


class ExportService:
    """Service for exporting data to CSV."""

    @staticmethod
    def export_group_members(db: Session, group_id: int) -> str:
        """Export group members with key metrics to CSV."""
        # Get group info
        group = db.query(Group).filter(Group.id == group_id).first()
        if not group:
            raise ValueError(f"Group {group_id} not found")

        # Get members
        memberships = (
            db.query(GroupMembership)
            .filter(GroupMembership.group_id == group_id)
            .all()
        )

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "NPWP", "Nama Wajib Pajak", "Jenis Entitas", "Status",
            "Omset 2022", "Omset 2023", "Omset 2024", "Omset 2025",
            "NPM 2025", "ETR 2025", "CTTOR 2025"
        ])

        for membership in memberships:
            taxpayer = membership.taxpayer

            # Get financial data
            financials = {
                f.tax_year: f for f in
                db.query(TaxpayerYearlyFinancial)
                .filter(TaxpayerYearlyFinancial.taxpayer_id == taxpayer.id)
                .all()
            }

            # Get ratios for 2025
            ratios_2025 = {
                r.ratio_code: r.ratio_value for r in
                db.query(TaxpayerYearlyRatio)
                .filter(
                    TaxpayerYearlyRatio.taxpayer_id == taxpayer.id,
                    TaxpayerYearlyRatio.tax_year == 2025
                )
                .all()
            }

            writer.writerow([
                taxpayer.npwp_masked,
                taxpayer.name,
                taxpayer.entity_type or "",
                taxpayer.status or "",
                float(financials.get(2022).turnover) if 2022 in financials and financials[2022].turnover else 0,
                float(financials.get(2023).turnover) if 2023 in financials and financials[2023].turnover else 0,
                float(financials.get(2024).turnover) if 2024 in financials and financials[2024].turnover else 0,
                float(financials.get(2025).turnover) if 2025 in financials and financials[2025].turnover else 0,
                float(ratios_2025.get("NPM", 0)),
                float(ratios_2025.get("ETR", 0)),
                float(ratios_2025.get("CTTOR", 0))
            ])

        return output.getvalue()

    @staticmethod
    def export_search_results(db: Session, taxpayer_ids: List[int]) -> str:
        """Export search results to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "NPWP", "Nama", "Jenis Entitas", "Status", "Alamat",
            "Omset 2025", "Status SPT 2025"
        ])

        taxpayers = db.query(Taxpayer).filter(Taxpayer.id.in_(taxpayer_ids)).all()

        for taxpayer in taxpayers:
            # Get latest financial
            financial_2025 = (
                db.query(TaxpayerYearlyFinancial)
                .filter(
                    TaxpayerYearlyFinancial.taxpayer_id == taxpayer.id,
                    TaxpayerYearlyFinancial.tax_year == 2025
                )
                .first()
            )

            writer.writerow([
                taxpayer.npwp_masked,
                taxpayer.name,
                taxpayer.entity_type or "",
                taxpayer.status or "",
                taxpayer.address or "",
                float(financial_2025.turnover) if financial_2025 and financial_2025.turnover else 0,
                financial_2025.spt_status if financial_2025 else ""
            ])

        return output.getvalue()
