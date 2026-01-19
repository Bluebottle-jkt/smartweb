# SmartWeb Database - Data Export Summary

**Export Date:** 2026-01-19
**Export Location:** D:\TaxObjectFinder\smartweb\

---

## 📊 Exported Data Files

### 1. **taxpayers_data.csv** (2,001 rows including header)
**Perusahaan / Companies / Wajib Pajak**

**Columns:**
- `id` - Unique taxpayer ID
- `npwp_masked` - Masked NPWP (Tax ID Number)
- `name` - Company name
- `entity_type` - Type: PT, CV, UD, Firma, Perorangan
- `address` - Full address
- `status` - Active/Inactive status
- `extra_metadata` - JSON with sector information
- `created_at` - Record creation timestamp

**Sample Data:**
- UD Cendana Global Bersama (NPWP: 10.000.***.***-***.100) - Sector: Manufaktur
- Firma Berkah Terpadu Jaya (NPWP: 11.000.***.***-***.100) - Sector: Energi

**Total in Database:** 30,000 taxpayers

---

### 2. **beneficial_owners_data.csv** (1,001 rows including header)
**Beneficial Owners / Pemilik Manfaat**

**Columns:**
- `id` - Unique beneficial owner ID
- `name` - Full name
- `id_number_masked` - Masked ID card number
- `nationality` - Nationality (Indonesia, Japan, Singapore, etc.)
- `notes` - Additional notes
- `created_at` - Record creation timestamp

**Sample Data:**
- Hendra Kusuma (ID: 3100********1000) - Indonesia
- Hendro Nurul Wijaya (ID: 3101********1001) - Indonesia
- Dian Nita Wibowo (ID: 3102********1002) - Japan
- Kurnia Kusumo (ID: 3103********1003) - Indonesia

**Total in Database:** 10,000 beneficial owners

---

### 3. **groups_data.csv** (501 rows including header)
**Business Groups / Grup Perusahaan**

**Columns:**
- `id` - Unique group ID
- `name` - Group name
- `sector` - Business sector
- `notes` - Description
- `extra_metadata` - JSON metadata
- `created_at` - Record creation timestamp

**Sample Data:**
- Grup Firma Abadi Buana Sejahtera - Sector: Jasa Keuangan
- Grup Firma Lestari Abadi Prima - Sector: Properti
- Grup Gemilang Global - Sector: Properti
- Grup UD Berlian Mandiri Terpadu - Sector: Transportasi

**Sectors Include:** Manufaktur, Perdagangan, Jasa Keuangan, Properti, Teknologi, Pertambangan, Konstruksi, Agrikultur, Transportasi, Telekomunikasi, Energi

**Total in Database:** 500 groups

---

### 4. **relationships_data.csv** (2,001 rows including header)
**Ownership Relationships / Struktur Kepemilikan**

**Columns:**
- `id` - Unique relationship ID
- `from_entity_type` - Source entity type (BENEFICIAL_OWNER, TAXPAYER)
- `from_entity_id` - Source entity ID
- `to_entity_type` - Target entity type (TAXPAYER)
- `to_entity_id` - Target entity ID
- `relationship_type` - OWNERSHIP, CONTROL, FAMILY
- `pct` - Ownership percentage (for OWNERSHIP type)
- `effective_from` - Relationship start date
- `effective_to` - Relationship end date (NULL if ongoing)
- `source` - Data source (BO Registry, Tax Return, etc.)
- `confidence` - Confidence score (0.0 - 1.0)
- `notes` - Additional notes
- `created_at` - Record creation timestamp

**Sample Data:**
- Beneficial Owner #1 owns 43.21% of Taxpayer #12902 (since 2024-03-01)
- Beneficial Owner #2 owns 83.70% of Taxpayer #5257 (since 2021-03-01)
- Beneficial Owner #3 owns 40.84% of Taxpayer #8022 (since 2018-05-01)

**Relationship Types:**
- **OWNERSHIP**: Direct ownership with percentage
- **CONTROL**: Control without ownership
- **FAMILY**: Family relationships between beneficial owners

---

### 5. **group_membership_data.csv** (2,001 rows including header)
**Group Memberships / Keanggotaan Grup**

**Columns:**
- `id` - Unique membership ID
- `group_id` - Reference to group table
- `taxpayer_id` - Reference to taxpayer table
- `role` - Parent, Subsidiary, Affiliate, Associate
- `start_date` - Membership start date
- `end_date` - Membership end date (NULL if ongoing)

**Sample Data:**
- Group #1 → Taxpayer #1 (Role: Affiliate, since 2021-02-05)
- Group #1 → Taxpayer #2 (Role: Subsidiary, since 2021-11-07)
- Group #1 → Taxpayer #3 (Role: Affiliate, since 2019-03-25)

**Membership Roles:**
- **Parent**: Parent company
- **Subsidiary**: Subsidiary/Anak Usaha
- **Affiliate**: Affiliated company
- **Associate**: Associated company

---

### 6. **officers_data.csv** (2,001 rows including header)
**Company Officers / Pengurus Perusahaan**

**Columns:**
- `id` - Unique officer ID
- `taxpayer_id` - Reference to taxpayer table
- `name` - Officer name
- `position` - Position/title
- `start_date` - Position start date
- `end_date` - Position end date (NULL if ongoing)
- `id_number_masked` - Masked ID card number
- `created_at` - Record creation timestamp

**Positions Include:**
- Direktur Utama (CEO)
- Komisaris Utama (President Commissioner)
- Direktur Keuangan (CFO)
- Komisaris (Commissioner)
- Direktur Operasional (COO)

---

### 7. **addresses_data.csv** (4,001 rows including header)
**Addresses / Alamat**

**Columns:**
- `id` - Unique address ID
- `taxpayer_id` - Reference to taxpayer table (NULL for BO addresses)
- `beneficial_owner_id` - Reference to beneficial owner table (NULL for taxpayer addresses)
- `address_type` - REGISTERED, OPERATIONAL, RESIDENTIAL
- `street` - Street address
- `city` - City
- `province` - Province
- `postal_code` - Postal code
- `country` - Country code
- `created_at` - Record creation timestamp

**Address Types:**
- **REGISTERED**: Registered office address
- **OPERATIONAL**: Operational/factory address
- **RESIDENTIAL**: Residential address (for beneficial owners)

---

### 8. **financial_data.csv** (1 row - EMPTY/HEADER ONLY)
**Yearly Financial Data / Data Keuangan Tahunan**

**Note:** This table appears to be empty in the current export. The table structure includes:
- Tax year (2022-2025)
- Revenue/Turnover (Omset)
- Loss compensation
- SPT status
- Other financial metrics

---

### 9. **affiliate_transactions_data.csv** (1 row - EMPTY/HEADER ONLY)
**Affiliate Transactions / Transaksi Afiliasi**

**Note:** This table appears to be empty in the current export. The table structure includes:
- Transaction type
- Direction (domestic/foreign)
- Amount
- Tax year
- Related parties

---

## 🗂️ Database Schema Overview

### Entity Types
1. **TAXPAYER** - Companies/Wajib Pajak (30,000 records)
2. **BENEFICIAL_OWNER** - Beneficial Owners (10,000 records)
3. **GROUP** - Business Groups (500 records)
4. **RELATIONSHIP** - Ownership/Control/Family links
5. **OFFICER** - Company officers/directors
6. **ADDRESS** - Physical addresses

### Key Relationships
- **Beneficial Owner → Taxpayer**: OWNERSHIP relationships with percentages
- **Taxpayer → Taxpayer**: Corporate ownership chains
- **Group ↔ Taxpayer**: Group memberships with roles
- **Taxpayer → Officer**: Management structure
- **Beneficial Owner → Beneficial Owner**: FAMILY relationships

---

## 📋 Menu Items Supported by This Data

Based on your application menu structure:

✅ **Peta Sebaran Group** - Supported by groups_data.csv
✅ **Eksplorasi Manual** - All data available for manual exploration
✅ **Pencarian NPWP** - taxpayers_data.csv with masked NPWPs

### **Kepemilikan (Ownership)**
✅ **Perusahaan** - taxpayers_data.csv (2,000 exported, 30,000 total)
✅ **Struktur Kepemilikan** - relationships_data.csv (ownership chains)
✅ **Beneficial Owner** - beneficial_owners_data.csv (1,000 exported, 10,000 total)
✅ **Group** - groups_data.csv (500 groups)
✅ **Pengendali** - relationships_data.csv (CONTROL type)
✅ **Anak Usaha** - group_membership_data.csv (Subsidiary role)
✅ **Keluarga Pemegang Saham** - relationships_data.csv (FAMILY type)
✅ **Group Pengurus** - officers_data.csv (company officers)

### **Transaksi Bisnis**
⚠️ **Transaksi Bisnis** - affiliate_transactions_data.csv (currently empty)

### **Jaringan Wajib Pajak**
✅ **Jaringan Wajib Pajak** - relationships_data.csv (full network graph)

---

## 🔗 Data Relationships Example

**Example: Tracing Ownership Chain**

```
Beneficial Owner #1 (Hendra Kusuma)
    ↓ owns 43.21%
Taxpayer #12902 (PT Example Company)
    ↓ member of
Group #1 (Grup Firma Abadi Buana Sejahtera)
    ↓ has officers
Officer: Direktur Utama
    ↓ located at
Address: Jakarta, Indonesia
```

---

## 📝 Notes

1. **Masked Data**: NPWP and ID numbers are masked for privacy (e.g., 10.000.***.***-***.100)
2. **Indonesian Companies**: All data uses Indonesian business structures (PT, CV, UD, Firma)
3. **Sectors**: Multiple business sectors represented (Manufaktur, Perdagangan, Jasa Keuangan, etc.)
4. **Time Range**: Dates range from 2018-2025
5. **Nationalities**: Mix of Indonesian and international beneficial owners (Indonesia, Japan, Singapore)

---

## 🚀 How to Use This Data

### Option 1: Import to Excel/Google Sheets
Open any CSV file in Excel or Google Sheets for analysis, filtering, and pivot tables.

### Option 2: Import to Database
Use these CSV files to populate your application's database:
```sql
COPY taxpayer FROM 'taxpayers_data.csv' WITH CSV HEADER;
COPY beneficial_owner FROM 'beneficial_owners_data.csv' WITH CSV HEADER;
-- etc.
```

### Option 3: Python/Pandas Analysis
```python
import pandas as pd

taxpayers = pd.read_csv('taxpayers_data.csv')
beneficiaries = pd.read_csv('beneficial_owners_data.csv')
relationships = pd.read_csv('relationships_data.csv')

# Analyze ownership structures
# Build network graphs
# Generate reports
```

### Option 4: API Access
The SmartWeb application is running with API endpoints:
- GET http://localhost:8100/taxpayers - List taxpayers
- GET http://localhost:8100/beneficial-owners - List beneficial owners
- GET http://localhost:8100/groups - List groups
- GET http://localhost:8100/docs - Full API documentation

---

## ⚠️ Missing Data Tables

The following tables have data in the database but weren't exported or are empty:
- `taxpayer_yearly_financial` - Financial metrics by year
- `taxpayer_yearly_affiliate_tx` - Affiliate transactions by year
- `taxpayer_yearly_ratio` - Financial ratios
- `taxpayer_treatment_history` - Tax treatment history
- `taxpayer_risk` - Risk assessments
- `derived_group` - Auto-generated groups from graph analysis

If you need these tables, they can be exported separately.

---

**End of Summary**
