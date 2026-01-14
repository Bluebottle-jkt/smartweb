# SmartWeb - Wajib Pajak Grup Task Force 2026

Production-quality web application untuk mendukung Task Force Wajib Pajak Grup 2026. Aplikasi ini menyediakan data populasi Grup dan Anggota Wajib Pajak dengan fitur pencarian cepat yang mendukung partial name matching dan pencarian berdasarkan Beneficial Owner.

## 🎯 Fitur Utama

- **Fast Keyword Search**: Pencarian cepat dengan pg_trgm untuk partial matching (cth: "grab" menemukan "Grabbike")
- **Beneficial Owner Search**: Cari entitas terkait berdasarkan nama BO (cth: "Wishnu Kusumo Agung")
- **Derived Groups (NEW)**: Deteksi otomatis grup berdasarkan relationship graph dengan algoritma Union-Find
- **Network Graph**: Visualisasi jaringan WP/BO berbasis root dengan depth sampai 5 + export PNG
- **Large Dataset**: 100 Grup, 1500+ Wajib Pajak, 300+ Beneficial Owners dengan data deterministik
- **Comprehensive Metrics**: Omset, transaksi afiliasi, rasio keuangan, SPT status, kompensasi rugi
- **Risk Assessment**: CRM risk level, Group Engine score, SR terkait
- **Treatment History**: Timeline tindakan dengan outcome tracking
- **Export to CSV**: Ekspor data grup dan hasil pencarian
- **RBAC**: Role-based access control (Admin, Analyst, Viewer)
- **Audit Log**: Pencatatan aksi penting untuk accountability

## 🏗️ Arsitektur Teknologi

### Backend
- **FastAPI** (Python 3.11+)
- **PostgreSQL 15+** dengan **pg_trgm** extension
- **SQLAlchemy 2.0** + Alembic migrations
- **Pydantic v2** untuk validasi
- **JWT** dengan httpOnly cookies
- **bcrypt** untuk password hashing
- Structured JSON logging

### Frontend
- **Next.js 14** (App Router)
- **TypeScript**
- **TailwindCSS**
- **TanStack Query** (React Query)
- **react-hook-form** + **Zod**
- **axios**

### Infrastructure
- **Docker** + **docker-compose**
- PostgreSQL container
- Backend container (uvicorn)
- Frontend container (Next.js dev server)

## 📋 Prerequisites

- Docker Desktop (atau Docker Engine + Docker Compose)
- 4GB+ RAM available
- Port 3000, 5432, dan 8000 tersedia

## 🚀 Quick Start

### 1. Clone atau navigasi ke direktori project

```bash
cd smartweb
```

### 2. Start semua services dengan Docker Compose

```bash
docker compose up --build
```

**Proses ini akan:**
1. Build backend dan frontend containers
2. Start PostgreSQL database
3. Run Alembic migrations (membuat schema dan enable pg_trgm)
4. Auto-generate seed data (100 groups, 1500 taxpayers, 300 BOs)
5. Start backend API di http://localhost:8000
6. Start frontend di http://localhost:3000

**Waktu startup pertama:** ~3-5 menit (build + seed data generation)

**Note**: Seed data akan mencakup ~3000 relationship edges (OWNERSHIP, CONTROL, FAMILY) untuk mendukung derived groups functionality.

### 3. Akses Aplikasi

Frontend: http://localhost:3000
Backend API Docs: http://localhost:8000/docs

### 4. Login dengan Kredensial Default

| Role | Username | Password |
|------|----------|----------|
| Admin | admin | admin123 |
| Analyst | analyst | analyst123 |
| Viewer | viewer | viewer123 |

## 🔗 Derived Groups - Automatic Group Discovery

**Derived Groups** adalah fitur untuk mendeteksi grup secara otomatis berdasarkan analisis **relationship graph** menggunakan algoritma graph theory. Fitur ini bersifat **additive** dan tidak mengganggu grup yang sudah di-curate manual.

### Curated Groups vs Derived Groups

| Aspek | Curated Groups | Derived Groups |
|-------|----------------|----------------|
| Sumber | Dibuat manual oleh analyst | Digenerate otomatis dari graph |
| Tabel | `business_group` | `derived_group` |
| Modifikasi | Bisa diedit manual | Read-only, regenerasi via API |
| Use Case | Grup yang sudah pasti/tervalidasi | Kandidat grup untuk investigasi |
| Status | Master data | Analytical output |

**Keduanya tetap ada** di sistem. Derived groups ditampilkan sebagai **kandidat** atau **suggestions** yang bisa divalidasi lebih lanjut oleh analyst.

### How It Works: Graph Analysis with Union-Find

Sistem menganalisis **relationship graph** untuk menemukan **connected components** (grup yang saling terhubung):

1. **Build Graph Edges**: Sistem membaca tabel `relationship` yang berisi:
   - `OWNERSHIP`: BO → Taxpayer atau Taxpayer → Taxpayer (dengan persentase kepemilikan)
   - `CONTROL`: Pengendalian langsung tanpa kepemilikan
   - `FAMILY`: Hubungan keluarga antar BO

2. **Apply Filters**: Edges yang masuk kriteria:
   - `OWNERSHIP` ≥ threshold persentase (default: 25%)
   - `CONTROL` selalu dihitung jika `control_as_affiliation` enabled
   - Shared BO jika `bo_shared_any` enabled
   - Confidence score ≥ `min_confidence` (default: 0.5)
   - Dalam range `effective_from` dan `effective_to`

3. **BFS Traversal**: Dari setiap node, lakukan BFS dengan batasan `max_hops` (default: 4) untuk menemukan entitas yang reachable.

4. **Union-Find Algorithm**: Gunakan **Disjoint Set Union** (Union-Find) dengan **path compression** dan **union by rank** untuk:
   - Merge nodes yang terhubung ke dalam satu component (grup)
   - Efisiensi O(α(n)) per operasi (α = inverse Ackermann, praktis konstan)

5. **Filter by Size**: Hanya simpan grup dengan minimal anggota ≥ `min_members` (default: 2)

6. **Store Evidence**: Setiap membership disimpan dengan evidence JSON berisi:
   - Paths ke anggota lain (relationship IDs yang menghubungkan)
   - Strength score berdasarkan connectivity
   - Timestamp derivasi

### Rule Set Configuration

Derived groups dihasilkan berdasarkan **GroupDefinitionRuleSet** yang bisa dikustomisasi:

```python
{
  "name": "Default UU PPh/PPN – Operational",
  "is_active": true,
  "min_members": 2,                           # Minimal anggota per grup
  "max_hops": 4,                              # Jarak maksimal dalam graph
  "direct_ownership_threshold_pct": 25,       # Threshold % untuk OWNERSHIP
  "include_relationship_types": ["OWNERSHIP", "CONTROL"],
  "control_as_affiliation": true,             # CONTROL dihitung sebagai afiliasi
  "bo_shared_any": true,                      # Shared BO = afiliasi
  "bo_shared_min_pct": 25,                    # Min % untuk shared BO
  "min_confidence": 0.5                       # Min confidence score
}
```

### Enabling Derived Groups Generation

**IMPORTANT**: Endpoint derivasi hanya bisa diakses jika `ALLOW_DERIVE=true` di environment variables. Ini adalah **safety mechanism** untuk mencegah generasi di production tanpa approval.

Di `docker-compose.yml`:

```yaml
backend:
  environment:
    ALLOW_DERIVE: "true"   # Enable derivation endpoint
```

Tanpa flag ini, endpoint akan return **403 Forbidden** bahkan untuk Admin.

### Running Derivation

**Via Admin UI**:
1. Login sebagai Admin
2. Akses http://localhost:3000/admin
3. Klik button "Generate Derived Groups"
4. Sistem akan tampilkan summary: jumlah grup, members, runtime

**Via API**:
```bash
curl -X POST http://localhost:8000/admin/derive-groups \
  -H "Cookie: access_token=<your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "rule_set_id": 1,
    "as_of_date": null
  }'
```

**Response**:
```json
{
  "number_of_groups": 45,
  "total_memberships": 287,
  "runtime_ms": 1234,
  "rule_set_id": 1,
  "rule_set_name": "Default UU PPh/PPN – Operational",
  "as_of_date": null
}
```

### Viewing Derived Groups

**In Taxpayer Detail Page**:
- Scroll ke section "**Grup Derivasi (Kandidat)**" (blue card)
- Lihat daftar derived groups yang mencakup taxpayer ini
- Klik group_key untuk detail

**In Beneficial Owner Detail Page**:
- Scroll ke section "**Grup Derivasi (Kandidat)**" (purple card)
- Lihat derived groups dari WP yang dimiliki BO ini

**In Derived Group Detail Page**:
- Akses via link dari taxpayer/BO page
- Lihat full member list dengan:
  - Taxpayer name, NPWP
  - Strength score (connectivity)
  - Evidence paths (relationship IDs)
- Filter dan sort members

**Via API**:
```bash
# List all derived groups
GET /derived-groups?rule_set_id=1&page=1&page_size=20

# Get specific group detail
GET /derived-groups/{id}

# Get derived groups for specific taxpayer
GET /derived-groups/taxpayers/{taxpayer_id}

# Get derived groups for specific BO
GET /derived-groups/beneficial-owners/{bo_id}
```

### Example Use Case

**Scenario**: Analyst ingin menemukan grup potensial berdasarkan shared ownership.

1. Seed data menghasilkan relationships:
   - BO "Budi Santoso" owns 40% of "PT Alpha"
   - BO "Budi Santoso" owns 35% of "PT Beta"
   - "PT Alpha" owns 30% of "PT Gamma"

2. Run derivation dengan `bo_shared_any=true`, `threshold=25%`, `max_hops=2`

3. **Union-Find logic**:
   - "PT Alpha" dan "PT Beta" di-union (shared BO "Budi Santoso")
   - "PT Alpha" dan "PT Gamma" di-union (direct ownership 30%)
   - Result: {PT Alpha, PT Beta, PT Gamma} dalam satu component

4. Sistem create `DerivedGroup` dengan 3 members, masing-masing dengan evidence JSON pointing ke relationship IDs.

5. Analyst bisa:
   - Lihat suggestion di taxpayer pages
   - Review evidence (siapa connect ke siapa)
   - Validasi apakah perlu dibuat `business_group` yang curated

## 📁 Struktur Project

```
smartweb/
├── docker-compose.yml
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       ├── 001_initial_migration.py
│   │       └── 002_add_derived_groups.py
│   └── app/
│       ├── main.py
│       ├── core/
│       │   ├── config.py
│       │   ├── security.py
│       │   └── logging.py
│       ├── db/
│       │   ├── base.py
│       │   ├── session.py
│       │   ├── seed.py
│       │   └── models/
│       │       ├── user.py
│       │       ├── group.py
│       │       ├── taxpayer.py
│       │       ├── beneficial_owner.py
│       │       ├── membership.py
│       │       ├── financial.py
│       │       ├── ratios.py
│       │       ├── affiliate_tx.py
│       │       ├── treatment.py
│       │       ├── risk.py
│       │       ├── audit.py
│       │       ├── recent_view.py
│       │       ├── relationship.py
│       │       ├── group_definition.py
│       │       └── derived_group.py
│       ├── api/
│       │   ├── deps.py
│       │   └── routers/
│       │       ├── auth.py
│       │       ├── search.py
│       │       ├── groups.py
│       │       ├── taxpayers.py
│       │       ├── beneficial_owners.py
│       │       ├── derived_groups.py
│       │       ├── exports.py
│       │       └── admin.py
│       ├── services/
│       │   ├── search_service.py
│       │   ├── export_service.py
│       │   ├── aggregate_service.py
│       │   └── group_derivation_service.py
│       └── tests/
│           ├── test_auth.py
│           ├── test_search.py
│           ├── test_aggregates.py
│           └── test_group_derivation.py
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── next.config.js
    ├── tailwind.config.ts
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   ├── page.tsx
        │   ├── providers.tsx
        │   ├── login/page.tsx
        │   ├── search/page.tsx
        │   ├── groups/[id]/page.tsx
        │   ├── taxpayers/[id]/page.tsx
        │   ├── beneficial-owners/[id]/page.tsx
        │   ├── derived-groups/[id]/page.tsx
        │   └── admin/page.tsx
        ├── components/
        │   ├── SearchBar.tsx
        │   ├── EntityCard.tsx
        │   └── RiskBadge.tsx
        ├── lib/
        │   ├── api.ts
        │   ├── auth.ts
        │   ├── utils.ts
        │   └── schemas.ts
        └── styles/
            └── globals.css
```

## 🔍 Penggunaan

### Pencarian Global

1. Di homepage, gunakan search bar besar
2. Ketik minimal 2 karakter (cth: "grab", "wishnu", "astra")
3. Pilih dari dropdown suggestions
4. Atau tekan Enter untuk full search

**Contoh pencarian:**
- "grab" → menemukan PT Grabbike Indonesia, PT Grab Express, dll
- "wishnu" → menemukan Beneficial Owner "Wishnu Kusumo Agung"
- "astra" → menemukan grup dan WP dengan kata "Astra"

### Detail Pages

- **Group Detail**: Lihat anggota, agregat omset, risiko grup, ekspor CSV
- **Taxpayer Detail**: Profil lengkap, data keuangan tahunan, rasio, treatment history, risiko
- **Beneficial Owner Detail**: Lihat WP yang dimiliki dan grup terkait

### Export Data

1. Masuk ke halaman Group Detail
2. Klik tombol "Ekspor ke CSV"
3. File CSV akan terdownload dengan data anggota + metrics

### Network Graph

1. Akses http://localhost:3000/network
2. Pilih **Root Type**, isi **Root ID**, pilih **Year** dan **Depth** (1-5)
3. Klik **Load Graph** untuk memuat jaringan terbatas
4. Gunakan **Layer Legend** untuk menampilkan/menyembunyikan layer
5. Klik **Export PNG** untuk menyimpan visualisasi

**Export PNG:**
- Gunakan **Scale 2x** untuk hasil tajam (3x jika butuh detail lebih)
- Pilih **Export Canvas** untuk graph saja, atau **Export View** untuk termasuk panel UI

**Tips performa:**
- Depth 4-5 disarankan dengan **max_nodes** lebih besar (Admin hingga 1500)
- Jika hasil terpotong, kurangi depth atau max_nodes

### Admin Functions (Admin Role Only)

Akses http://localhost:3000/admin

- Lihat statistik sistem
- **Reset Database & Re-seed**: Hapus semua data dan generate ulang (hanya untuk development!)

## 🔧 Konfigurasi

Environment variables di `docker-compose.yml`:

```yaml
# Backend
DATABASE_URL: Connection string PostgreSQL
SECRET_KEY: JWT secret key (ganti di production!)
ALLOW_DB_RESET: "true" untuk enable endpoint reset (BAHAYA di production)
ALLOW_DERIVE: "true" untuk enable derived groups generation endpoint
AUTO_SEED: "true" untuk auto-seed saat startup
SEED_GROUPS: 100
SEED_TAXPAYERS: 1500
SEED_BOS: 300
SEED_RNG: 20260109 (fixed seed untuk deterministic data)

# Frontend
NEXT_PUBLIC_API_URL: http://localhost:8000
```

## 🧪 Testing

### Run Backend Tests

```bash
cd backend
pytest app/tests/ -v
```

### Test Coverage

```bash
pytest app/tests/ --cov=app --cov-report=html
```

## 📊 Data Model

### Core Entities

- **Group**: Business groups (100 instances)
- **Taxpayer**: Wajib Pajak (1500+ instances)
- **BeneficialOwner**: Beneficial owners (300+ instances)

### Relationships

- `group_membership`: Many-to-many Group ↔ Taxpayer (curated groups)
- `beneficial_owner_taxpayer`: Many-to-many BO ↔ Taxpayer
- `relationship`: Generic graph edges (OWNERSHIP, CONTROL, FAMILY) between entities

### Derived Groups

- `group_definition_rule_set`: Configurable rules for group derivation
- `derived_group`: Auto-generated groups from relationship graph analysis
- `derived_group_membership`: Members of derived groups with evidence

### Yearly Data (2022-2025)

- `taxpayer_yearly_financial`: Omset, loss compensation, SPT status
- `taxpayer_yearly_ratio`: NPM, ETR, CTTOR
- `taxpayer_yearly_affiliate_tx`: Domestic/foreign affiliate transactions

### History & Risk

- `taxpayer_treatment_history`: Timeline of treatments
- `taxpayer_risk`: CRM levels, GroupEngine scores, SR codes

### System

- `user_account`: Users with RBAC
- `audit_log`: Action logging
- `user_recent_view`: Recently viewed entities

## 🎲 Seed Data Characteristics

Data generator menggunakan **fixed RNG seed (20260109)** untuk hasil deterministik:

- **100 Groups** dengan nama Indonesia + beberapa mengandung "Grab", "Astra", dll
- **1500+ Taxpayers** dengan 30+ mengandung substring "grab"
- **300+ Beneficial Owners** dengan nama Indonesia (10+ multi-token names)
- **~3000 Relationships**: OWNERSHIP (BO→Taxpayer, Taxpayer→Taxpayer chains), CONTROL, FAMILY
- **Turnover**: Log-normal distribution, realistic ranges
- **Ratios**: NPM (-0.20 to 0.40), ETR (0 to 0.35), CTTOR (0 to 5)
- **SPT Status**: Weighted realistic (Sudah Lapor > Belum Lapor)
- **Treatments**: 0-8 per taxpayer across 2022-2025
- **Risks**: CRM levels berdasarkan turnover, GroupEngine scores, SR codes
- **Default Rule Set**: "Default UU PPh/PPN – Operational" untuk derivation

Setiap run menghasilkan data identik, cocok untuk testing dan demo.

## 🔐 Security Features

- ✅ Password hashing dengan bcrypt
- ✅ JWT tokens dalam httpOnly cookies
- ✅ RBAC enforcement di backend + frontend
- ✅ SQL injection protection (SQLAlchemy ORM)
- ✅ Input validation (Pydantic)
- ✅ Audit logging untuk aksi penting
- ✅ Protected reset endpoint (ALLOW_DB_RESET env check)

## 📈 Performance Considerations

- **pg_trgm indexes** untuk fast partial matching
- **Composite indexes** untuk queries berulang (taxpayer_id + tax_year, dll)
- **Connection pooling** (SQLAlchemy pool_size=10, max_overflow=20)
- **React Query caching** di frontend
- **Bulk inserts** untuk seed data generation

## 🐛 Troubleshooting

### Port sudah digunakan

```bash
# Cek process yang menggunakan port
netstat -an | findstr :3000
netstat -an | findstr :8000
netstat -an | findstr :5432
```

### Rebuild dari scratch

```bash
docker compose down -v
docker compose up --build
```

### Reset database manually

1. Login sebagai Admin
2. Akses http://localhost:3000/admin
3. Klik "Reset Database & Re-seed"

Atau via API:
```bash
curl -X POST http://localhost:8000/admin/seed/reset-and-generate \
  -H "Cookie: access_token=<your_token>"
```

### Backend logs

```bash
docker compose logs backend -f
```

### Frontend logs

```bash
docker compose logs frontend -f
```

## 📝 API Documentation

Akses http://localhost:8000/docs untuk interactive OpenAPI documentation.

### Key Endpoints

**Auth:**
- `POST /auth/login` - Login
- `POST /auth/logout` - Logout
- `GET /auth/me` - Current user

**Search:**
- `GET /search/suggest?q=grab&limit=10` - Fast typeahead
- `GET /search?q=...&filters...` - Full search with pagination

**Entities:**
- `GET /groups` - List groups
- `GET /groups/{id}` - Group detail with aggregates
- `GET /taxpayers/{id}` - Taxpayer detail
- `GET /beneficial-owners/{id}` - BO detail

**Exports:**
- `GET /exports/groups/{id}/members` - Export group members CSV
- `POST /exports/search-results` - Export search results CSV

**Derived Groups:**
- `GET /derived-groups` - List derived groups with filters
- `GET /derived-groups/{id}` - Derived group detail with members
- `GET /derived-groups/taxpayers/{taxpayer_id}` - Groups for taxpayer
- `GET /derived-groups/beneficial-owners/{bo_id}` - Groups for BO

**Network Graph:**
- `GET /network/graph` - Bounded network graph (root, year, depth, max_nodes)
- `GET /network/graph/stats` - Layer counts summary

**Admin:**
- `POST /admin/seed/reset-and-generate` - Reset & re-seed (Admin only)
- `POST /admin/derive-groups` - Generate derived groups (Admin only, requires ALLOW_DERIVE)
- `GET /admin/stats` - System statistics

## 🎓 Development Notes

### Add New Migration

```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Run Seed Manually

```bash
cd backend
python -m app.db.seed --generate-large
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## 📄 License

Internal project untuk Tax Task Force 2026.

## 👥 Credits

Built with modern best practices for production-quality enterprise applications.

---

**Happy Searching! 🔍**
