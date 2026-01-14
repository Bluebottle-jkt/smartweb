"""
Large deterministic seed data generator for SmartWeb.

Generates:
- 100 Groups
- 1500+ Taxpayers
- 300+ Beneficial Owners
- Yearly metrics for 2022-2025
- Treatment histories
- Risk assessments
"""

import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any
from faker import Faker
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import engine, SessionLocal
from app.db.models import (
    UserAccount, UserRole, Group, Taxpayer, BeneficialOwner,
    GroupMembership, BeneficialOwnerTaxpayer,
    TaxpayerYearlyFinancial, TaxpayerYearlyRatio,
    TaxpayerYearlyAffiliateTx, TransactionDirection,
    TaxpayerTreatmentHistory, TaxpayerRisk,
    RiskSource, RiskLevel
)

# Fixed seed for deterministic data generation
SEED = settings.SEED_RNG
TAX_YEARS = [2022, 2023, 2024, 2025]

# Indonesian company prefixes and keywords
COMPANY_PREFIXES = [
    "Grup Nusantara", "Grup Mega", "Grup Indo", "Grup Sinar",
    "Grup Astra", "Grup Buana", "Grup Jaya", "Grup Wijaya",
    "Grup Mitra", "Grup Global", "Grup Sentosa", "Grup Pratama"
]

COMPANY_SUFFIXES = [
    "Sejahtera", "Makmur", "Jaya", "Abadi", "Cemerlang",
    "Gemilang", "Bersama", "Lestari", "Mandiri", "Terpadu"
]

SECTORS = [
    "Manufaktur", "Perdagangan", "Jasa Keuangan", "Properti",
    "Teknologi", "Pertambangan", "Konstruksi", "Agrikultur",
    "Transportasi", "Telekomunikasi"
]

ENTITY_TYPES = ["PT", "CV", "UD", "Firma", "Perorangan"]

TREATMENT_TYPES = ["SP2DK", "Klarifikasi", "Pemeriksaan", "Himbauan", "Penagihan", "Konseling"]
TREATMENT_OUTCOMES = ["Selesai", "Berlanjut", "Tidak Ada Koreksi", "Koreksi Positif", "Dalam Proses"]

SPT_STATUSES = ["Sudah Lapor", "Belum Lapor", "Pembetulan", "Nihil"]

TX_TYPES = ["Penjualan", "Pembelian", "Jasa", "Royalti", "Bunga", "Dividen"]

MEMBERSHIP_ROLES = ["Parent", "Subsidiary", "Affiliate", "Associate"]

# Names containing specific substrings for search testing
GRAB_VARIANTS = [
    "PT Grabbike Indonesia", "PT Grab Express", "CV Grab Teknologi",
    "PT Grabfood Services", "PT Grab Financial", "UD Grab Mart",
    "PT Grab Logistics", "CV Grab Pay", "PT Grab Wheels"
]

INDONESIAN_FIRST_NAMES = [
    "Wishnu", "Budi", "Siti", "Andi", "Dewi", "Agus", "Ratna", "Hendro",
    "Sri", "Bambang", "Indah", "Hadi", "Lestari", "Joko", "Nurul",
    "Rudi", "Maya", "Eko", "Wati", "Dian"
]

INDONESIAN_LAST_NAMES = [
    "Kusumo Agung", "Pratama", "Santoso", "Wijaya", "Kusuma", "Suharto",
    "Raharjo", "Setiawan", "Purwanto", "Suryanto", "Wibowo", "Hermawan",
    "Utomo", "Susanto", "Hartono"
]


def reset_database(db_engine) -> None:
    """Dangerously reset database. Only for development with ALLOW_DB_RESET=true."""
    if not settings.ALLOW_DB_RESET:
        raise RuntimeError("Database reset not allowed. Set ALLOW_DB_RESET=true")

    with db_engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO smartweb"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        conn.commit()


def mask_npwp(index: int) -> str:
    """Generate masked NPWP."""
    # Format: 12.***.***.*-***.345
    prefix = str(10 + (index % 90)).zfill(2)
    suffix = str(100 + (index // 90)).zfill(3)
    return f"{prefix}.***.***.*-***.{suffix}"


def mask_id_number(index: int) -> str:
    """Generate masked ID number."""
    prefix = str(3100 + (index % 7000)).zfill(4)
    suffix = str(1000 + (index % 9000)).zfill(4)
    return f"{prefix}********{suffix}"


def log_normal_value(rng: random.Random, mean: float, std: float, min_val: float = 0) -> Decimal:
    """Generate log-normal distributed value."""
    import math
    value = rng.lognormvariate(math.log(mean), std)
    return Decimal(str(max(min_val, round(value, 2))))


def generate_groups(db: Session, rng: random.Random, count: int) -> List[Group]:
    """Generate groups with diverse names including search test cases."""
    groups = []

    # Ensure we have groups with "Grab" in name
    grab_count = 3
    for i in range(grab_count):
        group = Group(
            name=f"Grup {GRAB_VARIANTS[i % len(GRAB_VARIANTS)].replace('PT ', '').replace('CV ', '').replace('UD ', '')}",
            sector=rng.choice(SECTORS),
            notes=f"Group containing Grab-related entities",
            metadata={"priority": "high", "category": "technology"}
        )
        groups.append(group)
        db.add(group)

    # Generate remaining groups with varied names
    for i in range(grab_count, count):
        prefix = rng.choice(COMPANY_PREFIXES)
        suffix = rng.choice(COMPANY_SUFFIXES)
        name = f"{prefix} {suffix}"

        group = Group(
            name=name,
            sector=rng.choice(SECTORS),
            notes=f"Business group in {rng.choice(SECTORS)} sector" if rng.random() > 0.5 else None,
            metadata={
                "established_year": rng.randint(1980, 2023),
                "employee_range": rng.choice(["1-50", "51-200", "201-1000", "1000+"])
            }
        )
        groups.append(group)
        db.add(group)

    db.commit()
    for group in groups:
        db.refresh(group)

    return groups


def generate_beneficial_owners(db: Session, rng: random.Random, count: int) -> List[BeneficialOwner]:
    """Generate beneficial owners with Indonesian names."""
    fake = Faker("id_ID")
    fake.seed_instance(SEED)

    bos = []

    # Generate BOs with specific names for testing
    special_names = [
        "Wishnu Kusumo Agung",
        "Budi Hartono Santoso",
        "Siti Dewi Kusuma"
    ]

    for i, name in enumerate(special_names[:min(len(special_names), count)]):
        bo = BeneficialOwner(
            name=name,
            id_number_masked=mask_id_number(i),
            nationality="Indonesia",
            notes=f"Primary beneficial owner #{i+1}"
        )
        bos.append(bo)
        db.add(bo)

    # Generate remaining BOs
    for i in range(len(special_names), count):
        first = rng.choice(INDONESIAN_FIRST_NAMES)
        middle = rng.choice(INDONESIAN_FIRST_NAMES) if rng.random() > 0.5 else ""
        last = rng.choice(INDONESIAN_LAST_NAMES)
        name = f"{first} {middle} {last}".strip()

        bo = BeneficialOwner(
            name=name,
            id_number_masked=mask_id_number(i),
            nationality=rng.choice(["Indonesia"] * 10 + ["Malaysia", "Singapore", "Netherlands", "Japan"]),
            notes=fake.sentence() if rng.random() > 0.7 else None
        )
        bos.append(bo)
        db.add(bo)

    db.commit()
    for bo in bos:
        db.refresh(bo)

    return bos


def generate_taxpayers(db: Session, rng: random.Random, groups: List[Group], count: int) -> List[Taxpayer]:
    """Generate taxpayers with realistic distribution."""
    fake = Faker("id_ID")
    fake.seed_instance(SEED)

    taxpayers = []

    # Ensure at least 30 taxpayers with "grab" in name
    grab_count = min(30, count // 50)
    for i in range(grab_count):
        variant = GRAB_VARIANTS[i % len(GRAB_VARIANTS)]
        taxpayer = Taxpayer(
            npwp_masked=mask_npwp(i),
            name=variant,
            entity_type="PT",
            address=fake.address(),
            status="Aktif",
            metadata={"verified": True, "category": "tech"}
        )
        taxpayers.append(taxpayer)
        db.add(taxpayer)

    # Generate remaining taxpayers
    for i in range(grab_count, count):
        entity_type = rng.choice(ENTITY_TYPES)
        company_words = [
            rng.choice(["Mandiri", "Jaya", "Sentosa", "Mitra", "Global", "Prima", "Utama", "Sejahtera"]),
            rng.choice(["Teknologi", "Perdagangan", "Industri", "Karya", "Pratama", "Abadi", "Makmur"])
        ]

        if rng.random() > 0.8:
            # Add some with common search terms
            company_words.insert(0, rng.choice(["Astra", "Sinar", "Indo", "Buana"]))

        name = f"{entity_type} {' '.join(company_words)}"

        taxpayer = Taxpayer(
            npwp_masked=mask_npwp(i),
            name=name,
            entity_type=entity_type,
            address=fake.address(),
            status=rng.choice(["Aktif"] * 8 + ["Non-Aktif", "Dalam Pemeriksaan"]),
            metadata={
                "phone": fake.phone_number() if rng.random() > 0.5 else None,
                "email": fake.company_email() if rng.random() > 0.5 else None
            }
        )
        taxpayers.append(taxpayer)
        db.add(taxpayer)

    db.commit()
    for taxpayer in taxpayers:
        db.refresh(taxpayer)

    return taxpayers


def create_group_memberships(db: Session, rng: random.Random, groups: List[Group], taxpayers: List[Taxpayer]) -> None:
    """Assign each taxpayer to exactly one group."""
    taxpayers_per_group = len(taxpayers) // len(groups)
    extra = len(taxpayers) % len(groups)

    taxpayer_idx = 0
    for group_idx, group in enumerate(groups):
        count = taxpayers_per_group + (1 if group_idx < extra else 0)

        for _ in range(count):
            if taxpayer_idx >= len(taxpayers):
                break

            membership = GroupMembership(
                group_id=group.id,
                taxpayer_id=taxpayers[taxpayer_idx].id,
                role=rng.choice(MEMBERSHIP_ROLES),
                start_date=date(rng.randint(2018, 2022), rng.randint(1, 12), rng.randint(1, 28))
            )
            db.add(membership)
            taxpayer_idx += 1

    db.commit()


def create_bo_taxpayer_relationships(db: Session, rng: random.Random, bos: List[BeneficialOwner], taxpayers: List[Taxpayer]) -> None:
    """Create BO-Taxpayer ownership relationships."""
    for bo in bos:
        num_owned = rng.randint(1, 10)
        owned_taxpayers = rng.sample(taxpayers, min(num_owned, len(taxpayers)))

        for taxpayer in owned_taxpayers:
            ownership = BeneficialOwnerTaxpayer(
                beneficial_owner_id=bo.id,
                taxpayer_id=taxpayer.id,
                ownership_pct=Decimal(str(round(rng.uniform(5, 95), 2)))
            )
            db.add(ownership)

    # Ensure each taxpayer has at least 1 BO
    for taxpayer in taxpayers:
        existing = db.query(BeneficialOwnerTaxpayer).filter_by(taxpayer_id=taxpayer.id).count()
        if existing == 0:
            bo = rng.choice(bos)
            ownership = BeneficialOwnerTaxpayer(
                beneficial_owner_id=bo.id,
                taxpayer_id=taxpayer.id,
                ownership_pct=Decimal(str(round(rng.uniform(25, 75), 2)))
            )
            db.add(ownership)

    db.commit()


def create_yearly_financials(db: Session, rng: random.Random, taxpayers: List[Taxpayer]) -> None:
    """Create yearly financial data for each taxpayer."""
    for taxpayer in taxpayers:
        base_turnover = log_normal_value(rng, 5_000_000_000, 1.5, 100_000_000)

        for year in TAX_YEARS:
            # Turnover grows or shrinks slightly year over year
            year_factor = 1 + rng.uniform(-0.15, 0.25)
            turnover = base_turnover * Decimal(str(year_factor))

            financial = TaxpayerYearlyFinancial(
                taxpayer_id=taxpayer.id,
                tax_year=year,
                turnover=turnover,
                loss_compensation=log_normal_value(rng, 100_000_000, 2, 0) if rng.random() > 0.7 else Decimal("0"),
                spt_status=rng.choices(SPT_STATUSES, weights=[60, 15, 20, 5])[0]
            )
            db.add(financial)

    db.commit()


def create_yearly_ratios(db: Session, rng: random.Random, taxpayers: List[Taxpayer]) -> None:
    """Create yearly ratio data (NPM, ETR, CTTOR)."""
    for taxpayer in taxpayers:
        for year in TAX_YEARS:
            # NPM: -0.20 to 0.40, skewed positive
            npm = Decimal(str(round(rng.gauss(0.08, 0.12), 4)))
            npm = max(Decimal("-0.20"), min(Decimal("0.40"), npm))

            # ETR: 0 to 0.35
            etr = Decimal(str(round(rng.betavariate(2, 3) * 0.35, 4)))

            # CTTOR: 0 to 5, skewed low
            cttor = Decimal(str(round(rng.lognormvariate(0, 0.8), 4)))
            cttor = min(Decimal("5.0"), cttor)

            for ratio_code, ratio_value in [("NPM", npm), ("ETR", etr), ("CTTOR", cttor)]:
                ratio = TaxpayerYearlyRatio(
                    taxpayer_id=taxpayer.id,
                    tax_year=year,
                    ratio_code=ratio_code,
                    ratio_value=ratio_value
                )
                db.add(ratio)

    db.commit()


def create_affiliate_transactions(db: Session, rng: random.Random, taxpayers: List[Taxpayer]) -> None:
    """Create affiliate transaction data."""
    for taxpayer in taxpayers:
        # Get taxpayer's turnover to correlate affiliate tx
        financials = db.query(TaxpayerYearlyFinancial).filter_by(taxpayer_id=taxpayer.id).all()

        for financial in financials:
            if not financial.turnover:
                continue

            # Affiliate transactions are 1-30% of turnover
            total_affiliate = financial.turnover * Decimal(str(rng.uniform(0.01, 0.30)))

            # Split into domestic and foreign
            domestic_ratio = rng.uniform(0.4, 0.9)
            domestic_total = total_affiliate * Decimal(str(domestic_ratio))
            foreign_total = total_affiliate - domestic_total

            # Distribute across transaction types
            for direction, total in [(TransactionDirection.DOMESTIC, domestic_total), (TransactionDirection.FOREIGN, foreign_total)]:
                num_types = rng.randint(1, 4)
                selected_types = rng.sample(TX_TYPES, num_types)

                remaining = total
                for i, tx_type in enumerate(selected_types):
                    if i == len(selected_types) - 1:
                        amount = remaining
                    else:
                        amount = remaining * Decimal(str(rng.uniform(0.1, 0.5)))
                        remaining -= amount

                    tx = TaxpayerYearlyAffiliateTx(
                        taxpayer_id=taxpayer.id,
                        tax_year=financial.tax_year,
                        direction=direction,
                        tx_type=tx_type,
                        tx_value=amount
                    )
                    db.add(tx)

    db.commit()


def create_treatment_histories(db: Session, rng: random.Random, taxpayers: List[Taxpayer]) -> None:
    """Create treatment history records."""
    for taxpayer in taxpayers:
        num_treatments = rng.randint(0, 8)

        for _ in range(num_treatments):
            year = rng.choice(TAX_YEARS)
            treatment_date = date(year, rng.randint(1, 12), rng.randint(1, 28))

            treatment = TaxpayerTreatmentHistory(
                taxpayer_id=taxpayer.id,
                treatment_date=treatment_date,
                treatment_type=rng.choice(TREATMENT_TYPES),
                notes=f"Treatment conducted in {year}" if rng.random() > 0.5 else None,
                outcome=rng.choice(TREATMENT_OUTCOMES),
                created_by=rng.choice(["admin", "analyst1", "analyst2"])
            )
            db.add(treatment)

    db.commit()


def create_risks(db: Session, rng: random.Random, taxpayers: List[Taxpayer]) -> None:
    """Create risk assessment data."""
    for taxpayer in taxpayers:
        # Get taxpayer's turnover to influence risk
        financials = db.query(TaxpayerYearlyFinancial).filter_by(taxpayer_id=taxpayer.id).all()

        avg_turnover = sum(f.turnover or 0 for f in financials) / len(financials) if financials else 0
        high_turnover = avg_turnover > 10_000_000_000

        # CRM risk
        for year in TAX_YEARS:
            if rng.random() > 0.3:  # Not all years have CRM risk
                weights = [20, 30, 35, 15] if high_turnover else [40, 35, 20, 5]
                risk_level = rng.choices(list(RiskLevel), weights=weights)[0]

                risk = TaxpayerRisk(
                    taxpayer_id=taxpayer.id,
                    tax_year=year,
                    risk_source=RiskSource.CRM,
                    risk_level=risk_level,
                    notes=f"CRM assessment for {year}"
                )
                db.add(risk)

        # GroupEngine risk score
        if rng.random() > 0.4:
            score = rng.uniform(20, 95) if high_turnover else rng.uniform(10, 60)
            risk = TaxpayerRisk(
                taxpayer_id=taxpayer.id,
                tax_year=None,
                risk_source=RiskSource.GROUP_ENGINE,
                risk_score=Decimal(str(round(score, 2))),
                notes="Group-level risk engine assessment"
            )
            db.add(risk)

        # SR-related
        if rng.random() > 0.85:
            sr_code = f"SR{rng.randint(1, 12):02d}_{rng.choice(['A', 'B', 'C', 'X'])}_{rng.randint(1, 20):02d}"
            risk = TaxpayerRisk(
                taxpayer_id=taxpayer.id,
                tax_year=rng.choice(TAX_YEARS),
                risk_source=RiskSource.SR,
                notes=f"SR code: {sr_code}"
            )
            db.add(risk)

    db.commit()


def create_admin_users(db: Session) -> None:
    """Create default admin users."""
    users = [
        UserAccount(
            username="admin",
            password_hash=get_password_hash("admin123"),
            role=UserRole.ADMIN
        ),
        UserAccount(
            username="analyst",
            password_hash=get_password_hash("analyst123"),
            role=UserRole.ANALYST
        ),
        UserAccount(
            username="viewer",
            password_hash=get_password_hash("viewer123"),
            role=UserRole.VIEWER
        )
    ]

    for user in users:
        db.add(user)

    db.commit()


def create_relationship_graph(db: Session, rng: random.Random, bos: List, taxpayers: List) -> None:
    """Create relationship graph for derived group derivation (~3000 relationships)."""
    from app.db.models.relationship import Relationship, EntityType, RelationshipType
    from decimal import Decimal

    relationships_created = 0

    # 1. BO -> Taxpayer OWNERSHIP relationships (based on existing BeneficialOwnerTaxpayer)
    from app.db.models.membership import BeneficialOwnerTaxpayer
    bo_tp_rels = db.query(BeneficialOwnerTaxpayer).all()

    for rel in bo_tp_rels:
        relationship = Relationship(
            from_entity_type=EntityType.BENEFICIAL_OWNER,
            from_entity_id=rel.beneficial_owner_id,
            to_entity_type=EntityType.TAXPAYER,
            to_entity_id=rel.taxpayer_id,
            relationship_type=RelationshipType.OWNERSHIP,
            pct=rel.ownership_pct,
            effective_from=date(2020, 1, 1),
            source="Internal BO Registry",
            confidence=Decimal("0.95")
        )
        db.add(relationship)
        relationships_created += 1

    # 2. Taxpayer -> Taxpayer OWNERSHIP chains (create indirect relationships)
    # Select ~500 random pairs to create ownership chains
    num_tp_tp_ownership = min(500, len(taxpayers) // 3)
    for _ in range(num_tp_tp_ownership):
        from_tp = rng.choice(taxpayers)
        to_tp = rng.choice([t for t in taxpayers if t.id != from_tp.id])

        pct = Decimal(str(rng.uniform(10, 60)))
        relationship = Relationship(
            from_entity_type=EntityType.TAXPAYER,
            from_entity_id=from_tp.id,
            to_entity_type=EntityType.TAXPAYER,
            to_entity_id=to_tp.id,
            relationship_type=RelationshipType.OWNERSHIP,
            pct=pct,
            effective_from=date(rng.randint(2018, 2023), rng.randint(1, 12), 1),
            source=rng.choice(["Saham Listing", "Akta Notaris", "LKPM"]),
            confidence=Decimal(str(rng.uniform(0.7, 1.0)))
        )
        db.add(relationship)
        relationships_created += 1

    # 3. Taxpayer -> Taxpayer CONTROL relationships (~200)
    num_control = min(200, len(taxpayers) // 8)
    for _ in range(num_control):
        from_tp = rng.choice(taxpayers)
        to_tp = rng.choice([t for t in taxpayers if t.id != from_tp.id])

        relationship = Relationship(
            from_entity_type=EntityType.TAXPAYER,
            from_entity_id=from_tp.id,
            to_entity_type=EntityType.TAXPAYER,
            to_entity_id=to_tp.id,
            relationship_type=RelationshipType.CONTROL,
            pct=None,  # Control doesn't require pct
            effective_from=date(rng.randint(2019, 2024), rng.randint(1, 12), 1),
            source="Board Control Analysis",
            confidence=Decimal(str(rng.uniform(0.8, 1.0))),
            notes="Control melalui dewan direksi dan komisaris"
        )
        db.add(relationship)
        relationships_created += 1

    # 4. FAMILY relationships between BOs (~100)
    num_family = min(100, len(bos) // 3)
    for _ in range(num_family):
        from_bo = rng.choice(bos)
        to_bo = rng.choice([b for b in bos if b.id != from_bo.id])

        relationship = Relationship(
            from_entity_type=EntityType.BENEFICIAL_OWNER,
            from_entity_id=from_bo.id,
            to_entity_type=EntityType.BENEFICIAL_OWNER,
            to_entity_id=to_bo.id,
            relationship_type=RelationshipType.FAMILY,
            pct=None,
            effective_from=None,
            source="KTP/KK Analysis",
            confidence=Decimal(str(rng.uniform(0.6, 0.9))),
            notes=rng.choice(["Suami/Istri", "Anak/Orang Tua", "Saudara Kandung"])
        )
        db.add(relationship)
        relationships_created += 1

    # 5. OTHER AFFILIATION (~100)
    num_other = min(100, len(taxpayers) // 15)
    for _ in range(num_other):
        from_tp = rng.choice(taxpayers)
        to_tp = rng.choice([t for t in taxpayers if t.id != from_tp.id])

        relationship = Relationship(
            from_entity_type=EntityType.TAXPAYER,
            from_entity_id=from_tp.id,
            to_entity_type=EntityType.TAXPAYER,
            to_entity_id=to_tp.id,
            relationship_type=RelationshipType.AFFILIATION_OTHER,
            pct=None,
            effective_from=date(rng.randint(2020, 2024), 1, 1),
            source="Transaction Pattern Analysis",
            confidence=Decimal(str(rng.uniform(0.5, 0.8))),
            notes="Afiliasi terdeteksi melalui pola transaksi"
        )
        db.add(relationship)
        relationships_created += 1

    db.commit()
    print(f"  - Created {relationships_created} relationship edges")


def create_default_rule_set(db: Session) -> None:
    """Create default group definition rule set."""
    from app.db.models.group_definition import GroupDefinitionRuleSet

    rule_set = GroupDefinitionRuleSet(
        name="Default UU PPh/PPN – Operational",
        is_active=True,
        min_members=2,
        max_hops=4,
        as_of_date=None,  # Current
        direct_ownership_threshold_pct=25,
        indirect_ownership_threshold_pct=25,
        include_relationship_types=['OWNERSHIP', 'CONTROL'],
        control_as_affiliation=True,
        min_confidence=0.7,
        bo_shared_any=True,
        bo_shared_min_pct=None
    )
    db.add(rule_set)
    db.commit()
    print("  - Created default rule set")


def generate_seed_data(db: Session) -> None:
    """Main seed data generation function."""
    print(f"Starting seed data generation with seed {SEED}...")

    # Initialize RNG with fixed seed
    rng = random.Random(SEED)

    print("Creating admin users...")
    create_admin_users(db)

    print(f"Generating {settings.SEED_GROUPS} groups...")
    groups = generate_groups(db, rng, settings.SEED_GROUPS)

    print(f"Generating {settings.SEED_BOS} beneficial owners...")
    bos = generate_beneficial_owners(db, rng, settings.SEED_BOS)

    print(f"Generating {settings.SEED_TAXPAYERS} taxpayers...")
    taxpayers = generate_taxpayers(db, rng, groups, settings.SEED_TAXPAYERS)

    print("Creating group memberships...")
    create_group_memberships(db, rng, groups, taxpayers)

    print("Creating BO-Taxpayer relationships...")
    create_bo_taxpayer_relationships(db, rng, bos, taxpayers)

    print("Creating yearly financial data...")
    create_yearly_financials(db, rng, taxpayers)

    print("Creating yearly ratio data...")
    create_yearly_ratios(db, rng, taxpayers)

    print("Creating affiliate transaction data...")
    create_affiliate_transactions(db, rng, taxpayers)

    print("Creating treatment histories...")
    create_treatment_histories(db, rng, taxpayers)

    print("Creating risk assessments...")
    create_risks(db, rng, taxpayers)

    print("Creating relationship graph...")
    create_relationship_graph(db, rng, bos, taxpayers)

    print("Creating default rule set...")
    create_default_rule_set(db)

    print("Seed data generation complete!")
    print(f"  - {len(groups)} groups")
    print(f"  - {len(taxpayers)} taxpayers")
    print(f"  - {len(bos)} beneficial owners")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed database with large dataset")
    parser.add_argument("--generate-large", action="store_true", help="Generate large seed dataset")
    parser.add_argument("--reset", action="store_true", help="Reset database before seeding (dangerous!)")

    args = parser.parse_args()

    if args.reset:
        print("WARNING: Resetting database...")
        reset_database(engine)
        print("Database reset complete. Running migrations...")
        import os
        os.system("alembic upgrade head")

    if args.generate_large:
        db = SessionLocal()
        try:
            generate_seed_data(db)
        finally:
            db.close()
