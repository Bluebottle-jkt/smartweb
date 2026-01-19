"""
Large-scale seed data generator for SmartWeb Proof of Concept.

Generates 100,000+ entities across multiple categories:
- Entity (Taxpayers/Companies): ~30,000
- Officers (Directors, Commissioners): ~25,000
- Addresses: ~15,000
- Intermediaries: ~5,000
- Beneficial Owners: ~10,000
- Additional Taxpayers: ~15,000

Total relationships: ~150,000+
"""

import random
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Tuple
from faker import Faker
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import engine, SessionLocal
from app.db.models import (
    UserAccount, UserRole, Group, Taxpayer, BeneficialOwner,
    Officer, Address, Intermediary,
    GroupMembership, BeneficialOwnerTaxpayer,
    TaxpayerYearlyFinancial, TaxpayerYearlyRatio,
    TaxpayerRisk, RiskSource, RiskLevel,
    Relationship, EntityType, RelationshipType
)

# Configuration
SEED = 20260115
BATCH_SIZE = 1000  # Commit every N records to avoid memory issues

# Entity counts for 100k total
ENTITY_COUNTS = {
    "taxpayers": 30000,
    "officers": 25000,
    "addresses": 15000,
    "intermediaries": 5000,
    "beneficial_owners": 10000,
    "groups": 500,
}

TAX_YEARS = [2022, 2023, 2024, 2025]

# Indonesian data
INDONESIAN_FIRST_NAMES = [
    "Wishnu", "Budi", "Siti", "Andi", "Dewi", "Agus", "Ratna", "Hendro",
    "Sri", "Bambang", "Indah", "Hadi", "Lestari", "Joko", "Nurul", "Rudi",
    "Maya", "Eko", "Wati", "Dian", "Putri", "Ahmad", "Fitri", "Wahyu",
    "Rizki", "Taufik", "Sari", "Kurnia", "Irwan", "Yanti", "Dwi", "Tri",
    "Hendra", "Yulia", "Feri", "Nita", "Adi", "Rina", "Sigit", "Wulan"
]

INDONESIAN_LAST_NAMES = [
    "Kusumo", "Pratama", "Santoso", "Wijaya", "Kusuma", "Suharto",
    "Raharjo", "Setiawan", "Purwanto", "Suryanto", "Wibowo", "Hermawan",
    "Utomo", "Susanto", "Hartono", "Gunawan", "Hidayat", "Nugroho",
    "Saputra", "Putra", "Permana", "Firmansyah", "Ramadhan", "Prasetyo",
    "Surya", "Cahya", "Aditya", "Mahendra", "Ardiansyah", "Prabowo"
]

COMPANY_PREFIXES = [
    "PT", "CV", "UD", "Firma", "PT Tbk", "PD", "Perum", "Koperasi"
]

COMPANY_WORDS = [
    "Mandiri", "Jaya", "Sentosa", "Mitra", "Global", "Prima", "Utama",
    "Sejahtera", "Makmur", "Abadi", "Gemilang", "Bersama", "Lestari",
    "Terpadu", "Berkah", "Karya", "Cipta", "Usaha", "Niaga", "Nusantara",
    "Indo", "Mega", "Sinar", "Buana", "Astra", "Rajawali", "Garuda",
    "Elang", "Merak", "Cendana", "Pusaka", "Permata", "Berlian", "Intan"
]

SECTORS = [
    "Manufaktur", "Perdagangan", "Jasa Keuangan", "Properti",
    "Teknologi", "Pertambangan", "Konstruksi", "Agrikultur",
    "Transportasi", "Telekomunikasi", "Kesehatan", "Pendidikan",
    "Pariwisata", "Energi", "Retail", "Makanan & Minuman"
]

OFFICER_POSITIONS = [
    "Direktur Utama", "Direktur", "Direktur Keuangan", "Direktur Operasional",
    "Komisaris Utama", "Komisaris", "Komisaris Independen",
    "Sekretaris Perusahaan", "CFO", "COO", "CEO"
]

INTERMEDIARY_TYPES = [
    "Kantor Hukum", "Kantor Akuntan Publik", "Notaris", "Konsultan Pajak",
    "Agen Pembentukan Perusahaan", "Trust Company", "Corporate Service Provider"
]

ADDRESS_TYPES = [
    "Kantor Pusat", "Kantor Cabang", "Gudang", "Pabrik",
    "Showroom", "Kantor Perwakilan", "Registered Office"
]

PROVINCES = [
    "DKI Jakarta", "Jawa Barat", "Jawa Tengah", "Jawa Timur",
    "Banten", "Yogyakarta", "Sumatera Utara", "Sumatera Selatan",
    "Kalimantan Timur", "Sulawesi Selatan", "Bali", "Riau"
]

CITIES = {
    "DKI Jakarta": ["Jakarta Pusat", "Jakarta Selatan", "Jakarta Barat", "Jakarta Timur", "Jakarta Utara"],
    "Jawa Barat": ["Bandung", "Bekasi", "Depok", "Bogor", "Cimahi", "Karawang"],
    "Jawa Tengah": ["Semarang", "Solo", "Pekalongan", "Magelang", "Salatiga"],
    "Jawa Timur": ["Surabaya", "Malang", "Sidoarjo", "Gresik", "Kediri"],
    "Banten": ["Tangerang", "Tangerang Selatan", "Serang", "Cilegon"],
    "Yogyakarta": ["Yogyakarta", "Sleman", "Bantul"],
    "Sumatera Utara": ["Medan", "Binjai", "Pematang Siantar"],
    "Sumatera Selatan": ["Palembang", "Prabumulih", "Lubuklinggau"],
    "Kalimantan Timur": ["Balikpapan", "Samarinda", "Bontang"],
    "Sulawesi Selatan": ["Makassar", "Parepare", "Palopo"],
    "Bali": ["Denpasar", "Badung", "Gianyar"],
    "Riau": ["Pekanbaru", "Dumai", "Bengkalis"],
}


def reset_database(db_engine) -> None:
    """Reset database schema."""
    if not settings.ALLOW_DB_RESET:
        raise RuntimeError("Database reset not allowed. Set ALLOW_DB_RESET=true")

    print("Resetting database...")
    with db_engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO smartweb"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        conn.commit()
    print("Database reset complete.")


def mask_npwp(index: int) -> str:
    """Generate masked NPWP."""
    prefix = str(10 + (index % 90)).zfill(2)
    suffix = str(100 + (index // 90) % 900).zfill(3)
    mid = str((index // 81000) % 1000).zfill(3)
    return f"{prefix}.{mid}.***.***-***.{suffix}"


def mask_id_number(index: int) -> str:
    """Generate masked ID number."""
    prefix = str(3100 + (index % 7000)).zfill(4)
    suffix = str(1000 + (index % 9000)).zfill(4)
    return f"{prefix}********{suffix}"


def generate_indonesian_name(rng: random.Random) -> str:
    """Generate a random Indonesian name."""
    first = rng.choice(INDONESIAN_FIRST_NAMES)
    middle = rng.choice(INDONESIAN_FIRST_NAMES) if rng.random() > 0.5 else ""
    last = rng.choice(INDONESIAN_LAST_NAMES)
    parts = [first, middle, last] if middle else [first, last]
    return " ".join(parts)


def generate_company_name(rng: random.Random) -> str:
    """Generate a random Indonesian company name."""
    prefix = rng.choice(COMPANY_PREFIXES)
    words = rng.sample(COMPANY_WORDS, rng.randint(2, 3))
    return f"{prefix} {' '.join(words)}"


def create_admin_users(db: Session) -> None:
    """Create default admin users."""
    users = [
        UserAccount(username="admin", password_hash=get_password_hash("admin123"), role=UserRole.ADMIN),
        UserAccount(username="analyst", password_hash=get_password_hash("analyst123"), role=UserRole.ANALYST),
        UserAccount(username="viewer", password_hash=get_password_hash("viewer123"), role=UserRole.VIEWER),
    ]
    for user in users:
        db.add(user)
    db.commit()
    print("  Created admin users")


def generate_groups(db: Session, rng: random.Random, count: int) -> List[Group]:
    """Generate groups."""
    print(f"  Generating {count} groups...")
    groups = []

    for i in range(count):
        name = f"Grup {generate_company_name(rng).replace('PT ', '').replace('CV ', '')}"
        group = Group(
            name=name,
            sector=rng.choice(SECTORS),
            notes=f"Business group #{i+1}",
            metadata={"established_year": rng.randint(1980, 2023)}
        )
        groups.append(group)
        db.add(group)

        if (i + 1) % BATCH_SIZE == 0:
            db.commit()
            print(f"    ... {i+1}/{count} groups")

    db.commit()
    for group in groups:
        db.refresh(group)

    return groups


def generate_taxpayers(db: Session, rng: random.Random, count: int) -> List[Taxpayer]:
    """Generate taxpayers (Entity category)."""
    print(f"  Generating {count} taxpayers...")
    fake = Faker("id_ID")
    fake.seed_instance(SEED)

    taxpayers = []

    for i in range(count):
        entity_type = rng.choice(COMPANY_PREFIXES[:5])  # PT, CV, UD, Firma, PT Tbk
        name = generate_company_name(rng)

        taxpayer = Taxpayer(
            npwp_masked=mask_npwp(i),
            name=name,
            entity_type=entity_type,
            address=fake.address(),
            status=rng.choices(["Aktif", "Non-Aktif", "Dalam Pemeriksaan"], weights=[85, 10, 5])[0],
            extra_metadata={"sector": rng.choice(SECTORS)}
        )
        taxpayers.append(taxpayer)
        db.add(taxpayer)

        if (i + 1) % BATCH_SIZE == 0:
            db.commit()
            print(f"    ... {i+1}/{count} taxpayers")

    db.commit()
    for tp in taxpayers:
        db.refresh(tp)

    return taxpayers


def generate_beneficial_owners(db: Session, rng: random.Random, count: int) -> List[BeneficialOwner]:
    """Generate beneficial owners."""
    print(f"  Generating {count} beneficial owners...")

    bos = []
    nationalities = ["Indonesia"] * 85 + ["Malaysia", "Singapore", "China", "Japan", "Netherlands"] * 3

    for i in range(count):
        name = generate_indonesian_name(rng)

        bo = BeneficialOwner(
            name=name,
            id_number_masked=mask_id_number(i),
            nationality=rng.choice(nationalities),
            notes=f"Beneficial Owner #{i+1}" if rng.random() > 0.8 else None
        )
        bos.append(bo)
        db.add(bo)

        if (i + 1) % BATCH_SIZE == 0:
            db.commit()
            print(f"    ... {i+1}/{count} beneficial owners")

    db.commit()
    for bo in bos:
        db.refresh(bo)

    return bos


def generate_officers(db: Session, rng: random.Random, count: int) -> List[Officer]:
    """Generate officers (directors, commissioners)."""
    print(f"  Generating {count} officers...")

    officers = []
    nationalities = ["Indonesia"] * 90 + ["Malaysia", "Singapore", "China", "Japan"] * 2 + ["Netherlands", "USA"]

    for i in range(count):
        name = generate_indonesian_name(rng)
        birth_year = rng.randint(1950, 1990)

        officer = Officer(
            name=name,
            id_number_masked=mask_id_number(100000 + i),
            position=rng.choice(OFFICER_POSITIONS),
            nationality=rng.choice(nationalities),
            birth_date=date(birth_year, rng.randint(1, 12), rng.randint(1, 28)),
            notes=None
        )
        officers.append(officer)
        db.add(officer)

        if (i + 1) % BATCH_SIZE == 0:
            db.commit()
            print(f"    ... {i+1}/{count} officers")

    db.commit()
    for officer in officers:
        db.refresh(officer)

    return officers


def generate_addresses(db: Session, rng: random.Random, count: int) -> List[Address]:
    """Generate addresses."""
    print(f"  Generating {count} addresses...")
    fake = Faker("id_ID")
    fake.seed_instance(SEED + 1)

    addresses = []

    for i in range(count):
        province = rng.choice(PROVINCES)
        city = rng.choice(CITIES.get(province, ["Unknown"]))

        address = Address(
            full_address=fake.address(),
            street=fake.street_address(),
            city=city,
            province=province,
            postal_code=fake.postcode(),
            country="Indonesia",
            latitude=rng.uniform(-8.5, 5.5) if rng.random() > 0.7 else None,
            longitude=rng.uniform(95, 141) if rng.random() > 0.7 else None,
            address_type=rng.choice(ADDRESS_TYPES),
            notes=None
        )
        addresses.append(address)
        db.add(address)

        if (i + 1) % BATCH_SIZE == 0:
            db.commit()
            print(f"    ... {i+1}/{count} addresses")

    db.commit()
    for addr in addresses:
        db.refresh(addr)

    return addresses


def generate_intermediaries(db: Session, rng: random.Random, count: int) -> List[Intermediary]:
    """Generate intermediaries (law firms, accountants, agents)."""
    print(f"  Generating {count} intermediaries...")
    fake = Faker("id_ID")
    fake.seed_instance(SEED + 2)

    intermediaries = []

    law_firm_names = ["Hadiputranto", "Soemadipradja", "Mochtar Karuwin", "Ali Budiardjo", "Lubis Ganie"]
    accounting_names = ["EY Indonesia", "PwC Indonesia", "Deloitte Indonesia", "KPMG Indonesia", "Grant Thornton"]

    for i in range(count):
        int_type = rng.choice(INTERMEDIARY_TYPES)

        if "Hukum" in int_type or "Notaris" in int_type:
            base_name = rng.choice(law_firm_names)
            name = f"{base_name} & Partners #{i % 100}"
        elif "Akuntan" in int_type:
            base_name = rng.choice(accounting_names)
            name = f"{base_name} - {rng.choice(['Jakarta', 'Surabaya', 'Bandung'])} #{i % 50}"
        else:
            name = f"{generate_company_name(rng)} Services"

        intermediary = Intermediary(
            name=name,
            intermediary_type=int_type,
            country=rng.choices(["Indonesia", "Singapore", "Malaysia", "Netherlands"], weights=[80, 10, 5, 5])[0],
            status=rng.choices(["Active", "Inactive"], weights=[90, 10])[0],
            address=fake.address(),
            notes=None
        )
        intermediaries.append(intermediary)
        db.add(intermediary)

        if (i + 1) % BATCH_SIZE == 0:
            db.commit()
            print(f"    ... {i+1}/{count} intermediaries")

    db.commit()
    for interm in intermediaries:
        db.refresh(interm)

    return intermediaries


def create_relationships(
    db: Session,
    rng: random.Random,
    taxpayers: List[Taxpayer],
    bos: List[BeneficialOwner],
    officers: List[Officer],
    addresses: List[Address],
    intermediaries: List[Intermediary]
) -> int:
    """Create relationships between all entity types."""
    print("  Creating relationships...")

    relationship_count = 0

    # 1. BO -> Taxpayer OWNERSHIP (~30,000 relationships)
    print("    Creating BO -> Taxpayer ownership relationships...")
    num_bo_tp = min(30000, len(bos) * 3)
    for i in range(num_bo_tp):
        bo = bos[i % len(bos)]
        tp = rng.choice(taxpayers)

        rel = Relationship(
            from_entity_type=EntityType.BENEFICIAL_OWNER,
            from_entity_id=bo.id,
            to_entity_type=EntityType.TAXPAYER,
            to_entity_id=tp.id,
            relationship_type=RelationshipType.OWNERSHIP,
            pct=Decimal(str(rng.uniform(5, 95))),
            effective_from=date(rng.randint(2018, 2024), rng.randint(1, 12), 1),
            source="BO Registry",
            confidence=Decimal(str(rng.uniform(0.7, 1.0)))
        )
        db.add(rel)
        relationship_count += 1

        if (i + 1) % BATCH_SIZE == 0:
            db.commit()
            print(f"      ... {i+1}/{num_bo_tp}")

    db.commit()

    # 2. Taxpayer -> Taxpayer OWNERSHIP chains (~20,000 relationships)
    print("    Creating Taxpayer -> Taxpayer ownership relationships...")
    num_tp_tp = min(20000, len(taxpayers) // 2)
    for i in range(num_tp_tp):
        from_tp = taxpayers[i % len(taxpayers)]
        to_tp = taxpayers[(i + rng.randint(1, 100)) % len(taxpayers)]

        if from_tp.id == to_tp.id:
            continue

        rel = Relationship(
            from_entity_type=EntityType.TAXPAYER,
            from_entity_id=from_tp.id,
            to_entity_type=EntityType.TAXPAYER,
            to_entity_id=to_tp.id,
            relationship_type=RelationshipType.OWNERSHIP,
            pct=Decimal(str(rng.uniform(10, 100))),
            effective_from=date(rng.randint(2018, 2024), rng.randint(1, 12), 1),
            source=rng.choice(["Akta Notaris", "Saham Listing", "LKPM"]),
            confidence=Decimal(str(rng.uniform(0.8, 1.0)))
        )
        db.add(rel)
        relationship_count += 1

        if (i + 1) % BATCH_SIZE == 0:
            db.commit()
            print(f"      ... {i+1}/{num_tp_tp}")

    db.commit()

    # 3. Officer -> Taxpayer CONTROL relationships (~30,000)
    print("    Creating Officer -> Taxpayer control relationships...")
    num_officer_tp = min(30000, len(officers))
    for i in range(num_officer_tp):
        officer = officers[i]
        # Each officer controls 1-3 taxpayers
        num_controlled = rng.randint(1, 3)
        for _ in range(num_controlled):
            tp = rng.choice(taxpayers)

            rel = Relationship(
                from_entity_type=EntityType.OFFICER,
                from_entity_id=officer.id,
                to_entity_type=EntityType.TAXPAYER,
                to_entity_id=tp.id,
                relationship_type=RelationshipType.CONTROL,
                pct=None,
                effective_from=date(rng.randint(2019, 2024), rng.randint(1, 12), 1),
                source="Board Registry",
                confidence=Decimal(str(rng.uniform(0.9, 1.0))),
                notes=officer.position
            )
            db.add(rel)
            relationship_count += 1

        if (i + 1) % BATCH_SIZE == 0:
            db.commit()
            print(f"      ... {i+1}/{num_officer_tp}")

    db.commit()

    # 4. Taxpayer -> Address relationships (~25,000)
    print("    Creating Taxpayer -> Address relationships...")
    num_tp_addr = min(25000, len(taxpayers))
    for i in range(num_tp_addr):
        tp = taxpayers[i]
        # Each taxpayer has 1-2 addresses
        num_addrs = rng.randint(1, 2)
        for _ in range(num_addrs):
            addr = rng.choice(addresses)

            rel = Relationship(
                from_entity_type=EntityType.TAXPAYER,
                from_entity_id=tp.id,
                to_entity_type=EntityType.ADDRESS,
                to_entity_id=addr.id,
                relationship_type=RelationshipType.AFFILIATION_OTHER,
                pct=None,
                effective_from=date(rng.randint(2018, 2024), 1, 1),
                source="Company Registry",
                notes=addr.address_type
            )
            db.add(rel)
            relationship_count += 1

        if (i + 1) % BATCH_SIZE == 0:
            db.commit()
            print(f"      ... {i+1}/{num_tp_addr}")

    db.commit()

    # 5. Intermediary -> Taxpayer relationships (~10,000)
    print("    Creating Intermediary -> Taxpayer relationships...")
    num_int_tp = min(10000, len(intermediaries) * 2)
    for i in range(num_int_tp):
        interm = intermediaries[i % len(intermediaries)]
        tp = rng.choice(taxpayers)

        rel = Relationship(
            from_entity_type=EntityType.INTERMEDIARY,
            from_entity_id=interm.id,
            to_entity_type=EntityType.TAXPAYER,
            to_entity_id=tp.id,
            relationship_type=RelationshipType.AFFILIATION_OTHER,
            pct=None,
            effective_from=date(rng.randint(2018, 2024), rng.randint(1, 12), 1),
            source="Formation Records",
            notes=interm.intermediary_type
        )
        db.add(rel)
        relationship_count += 1

        if (i + 1) % BATCH_SIZE == 0:
            db.commit()
            print(f"      ... {i+1}/{num_int_tp}")

    db.commit()

    # 6. BO Family relationships (~5,000)
    print("    Creating BO -> BO family relationships...")
    num_family = min(5000, len(bos) // 2)
    for i in range(num_family):
        from_bo = bos[i]
        to_bo = bos[(i + rng.randint(1, 50)) % len(bos)]

        if from_bo.id == to_bo.id:
            continue

        rel = Relationship(
            from_entity_type=EntityType.BENEFICIAL_OWNER,
            from_entity_id=from_bo.id,
            to_entity_type=EntityType.BENEFICIAL_OWNER,
            to_entity_id=to_bo.id,
            relationship_type=RelationshipType.FAMILY,
            pct=None,
            effective_from=None,
            source="KK Analysis",
            confidence=Decimal(str(rng.uniform(0.6, 0.95))),
            notes=rng.choice(["Suami/Istri", "Anak/Orang Tua", "Saudara Kandung"])
        )
        db.add(rel)
        relationship_count += 1

        if (i + 1) % BATCH_SIZE == 0:
            db.commit()
            print(f"      ... {i+1}/{num_family}")

    db.commit()

    # 7. Officer -> Officer relationships (~3,000)
    print("    Creating Officer -> Officer relationships...")
    num_officer_officer = min(3000, len(officers) // 5)
    for i in range(num_officer_officer):
        from_officer = officers[i]
        to_officer = officers[(i + rng.randint(1, 100)) % len(officers)]

        if from_officer.id == to_officer.id:
            continue

        rel = Relationship(
            from_entity_type=EntityType.OFFICER,
            from_entity_id=from_officer.id,
            to_entity_type=EntityType.OFFICER,
            to_entity_id=to_officer.id,
            relationship_type=rng.choice([RelationshipType.FAMILY, RelationshipType.AFFILIATION_OTHER]),
            pct=None,
            effective_from=None,
            source="Director Network Analysis",
            confidence=Decimal(str(rng.uniform(0.5, 0.9)))
        )
        db.add(rel)
        relationship_count += 1

        if (i + 1) % BATCH_SIZE == 0:
            db.commit()
            print(f"      ... {i+1}/{num_officer_officer}")

    db.commit()

    # 8. Shared Address relationships (~10,000)
    print("    Creating shared address relationships...")
    num_shared_addr = min(10000, len(addresses) * 2)
    for i in range(num_shared_addr):
        addr = addresses[i % len(addresses)]

        # Link multiple entities to same address
        entity_type = rng.choice([EntityType.OFFICER, EntityType.BENEFICIAL_OWNER])
        if entity_type == EntityType.OFFICER:
            entity_id = rng.choice(officers).id
        else:
            entity_id = rng.choice(bos).id

        rel = Relationship(
            from_entity_type=entity_type,
            from_entity_id=entity_id,
            to_entity_type=EntityType.ADDRESS,
            to_entity_id=addr.id,
            relationship_type=RelationshipType.AFFILIATION_OTHER,
            pct=None,
            effective_from=date(rng.randint(2018, 2024), 1, 1),
            source="Address Registry",
            notes="Registered address"
        )
        db.add(rel)
        relationship_count += 1

        if (i + 1) % BATCH_SIZE == 0:
            db.commit()
            print(f"      ... {i+1}/{num_shared_addr}")

    db.commit()

    return relationship_count


def create_group_memberships(db: Session, rng: random.Random, groups: List[Group], taxpayers: List[Taxpayer]) -> None:
    """Assign taxpayers to groups."""
    print("  Creating group memberships...")

    taxpayers_per_group = len(taxpayers) // len(groups)

    for i, tp in enumerate(taxpayers):
        group = groups[i // taxpayers_per_group] if i // taxpayers_per_group < len(groups) else rng.choice(groups)

        membership = GroupMembership(
            group_id=group.id,
            taxpayer_id=tp.id,
            role=rng.choice(["Parent", "Subsidiary", "Affiliate", "Associate"]),
            start_date=date(rng.randint(2018, 2022), rng.randint(1, 12), rng.randint(1, 28))
        )
        db.add(membership)

        if (i + 1) % BATCH_SIZE == 0:
            db.commit()
            print(f"    ... {i+1}/{len(taxpayers)}")

    db.commit()


def create_basic_financials(db: Session, rng: random.Random, taxpayers: List[Taxpayer]) -> None:
    """Create basic financial data (simplified for speed)."""
    print("  Creating basic financial data...")

    # Only create for a subset to keep it fast
    subset_size = min(10000, len(taxpayers))

    for i, tp in enumerate(taxpayers[:subset_size]):
        base_turnover = Decimal(str(rng.lognormvariate(23, 1.5)))  # ~10B IDR mean

        for year in TAX_YEARS:
            year_factor = 1 + rng.uniform(-0.15, 0.25)
            turnover = base_turnover * Decimal(str(year_factor))

            financial = TaxpayerYearlyFinancial(
                taxpayer_id=tp.id,
                tax_year=year,
                turnover=turnover,
                loss_compensation=Decimal("0"),
                spt_status=rng.choice(["Sudah Lapor", "Belum Lapor", "Nihil"])
            )
            db.add(financial)

        if (i + 1) % BATCH_SIZE == 0:
            db.commit()
            print(f"    ... {i+1}/{subset_size}")

    db.commit()


def generate_large_seed_data(db: Session) -> None:
    """Main seed data generation function for 100k entities."""
    print(f"\n{'='*60}")
    print("LARGE-SCALE SEED DATA GENERATION")
    print(f"{'='*60}")
    print(f"Seed: {SEED}")
    print(f"Target: ~100,000 entities + ~150,000 relationships")
    print(f"{'='*60}\n")

    rng = random.Random(SEED)

    # 1. Create admin users
    print("\n[1/9] Creating admin users...")
    create_admin_users(db)

    # 2. Generate groups
    print(f"\n[2/9] Generating groups...")
    groups = generate_groups(db, rng, ENTITY_COUNTS["groups"])

    # 3. Generate taxpayers (Entity category)
    print(f"\n[3/9] Generating taxpayers (Entity)...")
    taxpayers = generate_taxpayers(db, rng, ENTITY_COUNTS["taxpayers"])

    # 4. Generate beneficial owners
    print(f"\n[4/9] Generating beneficial owners...")
    bos = generate_beneficial_owners(db, rng, ENTITY_COUNTS["beneficial_owners"])

    # 5. Generate officers
    print(f"\n[5/9] Generating officers...")
    officers = generate_officers(db, rng, ENTITY_COUNTS["officers"])

    # 6. Generate addresses
    print(f"\n[6/9] Generating addresses...")
    addresses = generate_addresses(db, rng, ENTITY_COUNTS["addresses"])

    # 7. Generate intermediaries
    print(f"\n[7/9] Generating intermediaries...")
    intermediaries = generate_intermediaries(db, rng, ENTITY_COUNTS["intermediaries"])

    # 8. Create relationships
    print(f"\n[8/9] Creating relationships between entities...")
    rel_count = create_relationships(db, rng, taxpayers, bos, officers, addresses, intermediaries)

    # 9. Create group memberships
    print(f"\n[9/9] Creating group memberships...")
    create_group_memberships(db, rng, groups, taxpayers)

    # Optional: Create basic financials (can be slow)
    # print(f"\n[Bonus] Creating basic financial data...")
    # create_basic_financials(db, rng, taxpayers)

    # Summary
    total_entities = sum(ENTITY_COUNTS.values())
    print(f"\n{'='*60}")
    print("SEED DATA GENERATION COMPLETE!")
    print(f"{'='*60}")
    print(f"  Groups:           {ENTITY_COUNTS['groups']:>10,}")
    print(f"  Taxpayers:        {ENTITY_COUNTS['taxpayers']:>10,}")
    print(f"  Beneficial Owners:{ENTITY_COUNTS['beneficial_owners']:>10,}")
    print(f"  Officers:         {ENTITY_COUNTS['officers']:>10,}")
    print(f"  Addresses:        {ENTITY_COUNTS['addresses']:>10,}")
    print(f"  Intermediaries:   {ENTITY_COUNTS['intermediaries']:>10,}")
    print(f"  --------------------------------")
    print(f"  Total Entities:   {total_entities:>10,}")
    print(f"  Relationships:    {rel_count:>10,}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate large seed dataset for SmartWeb PoC")
    parser.add_argument("--reset", action="store_true", help="Reset database before seeding")
    parser.add_argument("--scale", type=float, default=1.0, help="Scale factor (0.1 = 10k, 1.0 = 100k)")

    args = parser.parse_args()

    # Apply scale factor
    if args.scale != 1.0:
        for key in ENTITY_COUNTS:
            ENTITY_COUNTS[key] = max(10, int(ENTITY_COUNTS[key] * args.scale))

    if args.reset:
        reset_database(engine)
        print("Running migrations...")
        import os
        os.system("alembic upgrade head")

    db = SessionLocal()
    try:
        generate_large_seed_data(db)
    except Exception as e:
        print(f"\nError during seed generation: {e}")
        db.rollback()
        raise
    finally:
        db.close()
