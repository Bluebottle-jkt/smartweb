"""
Seed Kanwil DJP and KPP reference data for Indonesia.

Based on the actual DJP organizational structure (simplified/representative).
Call seed_geography_data(db) once after migration.
"""
from __future__ import annotations

import logging
from sqlalchemy.orm import Session
from app.db.models.geography import City, KPP, Kanwil, Province

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Province data
# ---------------------------------------------------------------------------
PROVINCES = [
    {"name": "DKI Jakarta", "code": "31"},
    {"name": "Jawa Barat", "code": "32"},
    {"name": "Jawa Tengah", "code": "33"},
    {"name": "DI Yogyakarta", "code": "34"},
    {"name": "Jawa Timur", "code": "35"},
    {"name": "Banten", "code": "36"},
    {"name": "Bali", "code": "51"},
    {"name": "Sumatera Utara", "code": "12"},
    {"name": "Sumatera Selatan", "code": "16"},
    {"name": "Riau", "code": "14"},
    {"name": "Kalimantan Timur", "code": "64"},
    {"name": "Sulawesi Selatan", "code": "73"},
    {"name": "Papua", "code": "91"},
    {"name": "Nusa Tenggara Timur", "code": "53"},
    {"name": "Sulawesi Utara", "code": "71"},
]

# ---------------------------------------------------------------------------
# Major cities with lat/lon
# ---------------------------------------------------------------------------
CITIES = [
    {"name": "Jakarta Selatan", "province": "DKI Jakarta", "lat": -6.26, "lon": 106.81},
    {"name": "Jakarta Pusat",   "province": "DKI Jakarta", "lat": -6.17, "lon": 106.83},
    {"name": "Jakarta Utara",   "province": "DKI Jakarta", "lat": -6.12, "lon": 106.87},
    {"name": "Jakarta Barat",   "province": "DKI Jakarta", "lat": -6.17, "lon": 106.73},
    {"name": "Jakarta Timur",   "province": "DKI Jakarta", "lat": -6.22, "lon": 106.90},
    {"name": "Bandung",         "province": "Jawa Barat",  "lat": -6.92, "lon": 107.61},
    {"name": "Bekasi",          "province": "Jawa Barat",  "lat": -6.24, "lon": 106.99},
    {"name": "Bogor",           "province": "Jawa Barat",  "lat": -6.60, "lon": 106.80},
    {"name": "Depok",           "province": "Jawa Barat",  "lat": -6.40, "lon": 106.82},
    {"name": "Semarang",        "province": "Jawa Tengah", "lat": -7.00, "lon": 110.41},
    {"name": "Solo",            "province": "Jawa Tengah", "lat": -7.57, "lon": 110.83},
    {"name": "Yogyakarta",      "province": "DI Yogyakarta","lat": -7.80, "lon": 110.36},
    {"name": "Surabaya",        "province": "Jawa Timur",  "lat": -7.25, "lon": 112.75},
    {"name": "Malang",          "province": "Jawa Timur",  "lat": -7.97, "lon": 112.63},
    {"name": "Sidoarjo",        "province": "Jawa Timur",  "lat": -7.45, "lon": 112.72},
    {"name": "Tangerang",       "province": "Banten",      "lat": -6.18, "lon": 106.64},
    {"name": "Serang",          "province": "Banten",      "lat": -6.12, "lon": 106.15},
    {"name": "Denpasar",        "province": "Bali",        "lat": -8.65, "lon": 115.21},
    {"name": "Medan",           "province": "Sumatera Utara","lat": 3.58, "lon": 98.67},
    {"name": "Palembang",       "province": "Sumatera Selatan","lat": -2.99, "lon": 104.76},
    {"name": "Pekanbaru",       "province": "Riau",        "lat": 0.53,  "lon": 101.45},
    {"name": "Balikpapan",      "province": "Kalimantan Timur","lat": -1.27,"lon": 116.83},
    {"name": "Samarinda",       "province": "Kalimantan Timur","lat": -0.50,"lon": 117.15},
    {"name": "Makassar",        "province": "Sulawesi Selatan","lat": -5.15,"lon": 119.42},
    {"name": "Jayapura",        "province": "Papua",       "lat": -2.53, "lon": 140.72},
    {"name": "Kupang",          "province": "Nusa Tenggara Timur","lat": -10.18,"lon": 123.61},
    {"name": "Manado",          "province": "Sulawesi Utara","lat": 1.48, "lon": 124.84},
]

# ---------------------------------------------------------------------------
# Kanwil DJP data (representative subset of 34 Kanwil)
# ---------------------------------------------------------------------------
KANWILS = [
    {"name": "Kanwil DJP Jakarta Pusat",       "code": "KW01", "province": "DKI Jakarta",       "lat": -6.17, "lon": 106.83},
    {"name": "Kanwil DJP Jakarta Selatan I",   "code": "KW02", "province": "DKI Jakarta",       "lat": -6.26, "lon": 106.81},
    {"name": "Kanwil DJP Jakarta Selatan II",  "code": "KW03", "province": "DKI Jakarta",       "lat": -6.28, "lon": 106.79},
    {"name": "Kanwil DJP Jakarta Barat",       "code": "KW04", "province": "DKI Jakarta",       "lat": -6.17, "lon": 106.73},
    {"name": "Kanwil DJP Jakarta Timur",       "code": "KW05", "province": "DKI Jakarta",       "lat": -6.22, "lon": 106.90},
    {"name": "Kanwil DJP Jakarta Utara",       "code": "KW06", "province": "DKI Jakarta",       "lat": -6.12, "lon": 106.87},
    {"name": "Kanwil DJP Banten",              "code": "KW07", "province": "Banten",            "lat": -6.18, "lon": 106.64},
    {"name": "Kanwil DJP Jawa Barat I",        "code": "KW08", "province": "Jawa Barat",        "lat": -6.92, "lon": 107.61},
    {"name": "Kanwil DJP Jawa Barat II",       "code": "KW09", "province": "Jawa Barat",        "lat": -6.24, "lon": 106.99},
    {"name": "Kanwil DJP Jawa Tengah I",       "code": "KW10", "province": "Jawa Tengah",       "lat": -7.00, "lon": 110.41},
    {"name": "Kanwil DJP Jawa Tengah II",      "code": "KW11", "province": "Jawa Tengah",       "lat": -7.57, "lon": 110.83},
    {"name": "Kanwil DJP DI Yogyakarta",       "code": "KW12", "province": "DI Yogyakarta",     "lat": -7.80, "lon": 110.36},
    {"name": "Kanwil DJP Jawa Timur I",        "code": "KW13", "province": "Jawa Timur",        "lat": -7.25, "lon": 112.75},
    {"name": "Kanwil DJP Jawa Timur II",       "code": "KW14", "province": "Jawa Timur",        "lat": -7.45, "lon": 112.72},
    {"name": "Kanwil DJP Jawa Timur III",      "code": "KW15", "province": "Jawa Timur",        "lat": -7.97, "lon": 112.63},
    {"name": "Kanwil DJP Bali",                "code": "KW16", "province": "Bali",              "lat": -8.65, "lon": 115.21},
    {"name": "Kanwil DJP Sumatera Utara I",    "code": "KW17", "province": "Sumatera Utara",    "lat": 3.58,  "lon": 98.67},
    {"name": "Kanwil DJP Sumatera Utara II",   "code": "KW18", "province": "Sumatera Utara",    "lat": 3.40,  "lon": 98.80},
    {"name": "Kanwil DJP Sumatera Selatan",    "code": "KW19", "province": "Sumatera Selatan",  "lat": -2.99, "lon": 104.76},
    {"name": "Kanwil DJP Riau & Kepri",        "code": "KW20", "province": "Riau",              "lat": 0.53,  "lon": 101.45},
    {"name": "Kanwil DJP Kalimantan Timur",    "code": "KW21", "province": "Kalimantan Timur",  "lat": -1.27, "lon": 116.83},
    {"name": "Kanwil DJP Sulawesi Selatan",    "code": "KW22", "province": "Sulawesi Selatan",  "lat": -5.15, "lon": 119.42},
    {"name": "Kanwil DJP Papua",               "code": "KW23", "province": "Papua",             "lat": -2.53, "lon": 140.72},
    {"name": "Kanwil DJP Nusa Tenggara",       "code": "KW24", "province": "Nusa Tenggara Timur","lat":-10.18, "lon": 123.61},
]

# ---------------------------------------------------------------------------
# KPP data: representative offices per Kanwil
# ---------------------------------------------------------------------------
KPPS = [
    # Jakarta Pusat
    {"name": "KPP Pratama Jakarta Gambir Satu",      "code": "KPP001", "kanwil": "KW01", "city": "Jakarta Pusat"},
    {"name": "KPP Pratama Jakarta Gambir Dua",        "code": "KPP002", "kanwil": "KW01", "city": "Jakarta Pusat"},
    {"name": "KPP Pratama Jakarta Sawah Besar Satu",  "code": "KPP003", "kanwil": "KW01", "city": "Jakarta Pusat"},
    {"name": "KPP Madya Jakarta Pusat",               "code": "KPP004", "kanwil": "KW01", "city": "Jakarta Pusat"},
    # Jakarta Selatan I
    {"name": "KPP Pratama Jakarta Kebayoran Baru Satu","code": "KPP011","kanwil": "KW02", "city": "Jakarta Selatan"},
    {"name": "KPP Pratama Jakarta Kebayoran Baru Dua", "code": "KPP012","kanwil": "KW02", "city": "Jakarta Selatan"},
    {"name": "KPP Pratama Jakarta Mampang Prapatan",   "code": "KPP013","kanwil": "KW02", "city": "Jakarta Selatan"},
    {"name": "KPP Madya Jakarta Selatan",              "code": "KPP014","kanwil": "KW02", "city": "Jakarta Selatan"},
    # Jakarta Selatan II
    {"name": "KPP Pratama Jakarta Pasar Minggu",       "code": "KPP021","kanwil": "KW03", "city": "Jakarta Selatan"},
    {"name": "KPP Pratama Jakarta Pesanggrahan",       "code": "KPP022","kanwil": "KW03", "city": "Jakarta Selatan"},
    # Jakarta Barat
    {"name": "KPP Pratama Jakarta Kebon Jeruk Satu",   "code": "KPP031","kanwil": "KW04", "city": "Jakarta Barat"},
    {"name": "KPP Pratama Jakarta Cengkareng",         "code": "KPP032","kanwil": "KW04", "city": "Jakarta Barat"},
    {"name": "KPP Madya Jakarta Barat",                "code": "KPP033","kanwil": "KW04", "city": "Jakarta Barat"},
    # Jakarta Timur
    {"name": "KPP Pratama Jakarta Duren Sawit",        "code": "KPP041","kanwil": "KW05", "city": "Jakarta Timur"},
    {"name": "KPP Pratama Jakarta Matraman",           "code": "KPP042","kanwil": "KW05", "city": "Jakarta Timur"},
    {"name": "KPP Madya Jakarta Timur",                "code": "KPP043","kanwil": "KW05", "city": "Jakarta Timur"},
    # Jakarta Utara
    {"name": "KPP Pratama Jakarta Penjaringan",        "code": "KPP051","kanwil": "KW06", "city": "Jakarta Utara"},
    {"name": "KPP Pratama Jakarta Tanjung Priok",      "code": "KPP052","kanwil": "KW06", "city": "Jakarta Utara"},
    # Banten
    {"name": "KPP Pratama Tangerang Timur",            "code": "KPP061","kanwil": "KW07", "city": "Tangerang"},
    {"name": "KPP Pratama Tangerang Barat",            "code": "KPP062","kanwil": "KW07", "city": "Tangerang"},
    {"name": "KPP Madya Tangerang",                    "code": "KPP063","kanwil": "KW07", "city": "Tangerang"},
    # Jawa Barat I
    {"name": "KPP Pratama Bandung Karees",             "code": "KPP071","kanwil": "KW08", "city": "Bandung"},
    {"name": "KPP Pratama Bandung Bojonagara",         "code": "KPP072","kanwil": "KW08", "city": "Bandung"},
    {"name": "KPP Madya Bandung",                      "code": "KPP073","kanwil": "KW08", "city": "Bandung"},
    # Jawa Barat II
    {"name": "KPP Pratama Bekasi Utara",               "code": "KPP081","kanwil": "KW09", "city": "Bekasi"},
    {"name": "KPP Pratama Bekasi Selatan",             "code": "KPP082","kanwil": "KW09", "city": "Bekasi"},
    {"name": "KPP Pratama Depok Sawangan",             "code": "KPP083","kanwil": "KW09", "city": "Depok"},
    # Jawa Tengah I
    {"name": "KPP Pratama Semarang Barat",             "code": "KPP091","kanwil": "KW10", "city": "Semarang"},
    {"name": "KPP Pratama Semarang Timur",             "code": "KPP092","kanwil": "KW10", "city": "Semarang"},
    {"name": "KPP Madya Semarang",                     "code": "KPP093","kanwil": "KW10", "city": "Semarang"},
    # Jawa Tengah II
    {"name": "KPP Pratama Surakarta",                  "code": "KPP101","kanwil": "KW11", "city": "Solo"},
    {"name": "KPP Pratama Klaten",                     "code": "KPP102","kanwil": "KW11", "city": "Solo"},
    # DI Yogyakarta
    {"name": "KPP Pratama Yogyakarta",                 "code": "KPP111","kanwil": "KW12", "city": "Yogyakarta"},
    {"name": "KPP Pratama Wates",                      "code": "KPP112","kanwil": "KW12", "city": "Yogyakarta"},
    # Jawa Timur I
    {"name": "KPP Pratama Surabaya Gubeng",            "code": "KPP121","kanwil": "KW13", "city": "Surabaya"},
    {"name": "KPP Pratama Surabaya Krembangan",        "code": "KPP122","kanwil": "KW13", "city": "Surabaya"},
    {"name": "KPP Madya Surabaya",                     "code": "KPP123","kanwil": "KW13", "city": "Surabaya"},
    # Jawa Timur II
    {"name": "KPP Pratama Sidoarjo Barat",             "code": "KPP131","kanwil": "KW14", "city": "Sidoarjo"},
    {"name": "KPP Pratama Sidoarjo Utara",             "code": "KPP132","kanwil": "KW14", "city": "Sidoarjo"},
    # Jawa Timur III
    {"name": "KPP Pratama Malang Selatan",             "code": "KPP141","kanwil": "KW15", "city": "Malang"},
    {"name": "KPP Pratama Malang Utara",               "code": "KPP142","kanwil": "KW15", "city": "Malang"},
    # Bali
    {"name": "KPP Pratama Denpasar Barat",             "code": "KPP151","kanwil": "KW16", "city": "Denpasar"},
    {"name": "KPP Pratama Denpasar Timur",             "code": "KPP152","kanwil": "KW16", "city": "Denpasar"},
    # Sumatera Utara I
    {"name": "KPP Pratama Medan Belawan",              "code": "KPP161","kanwil": "KW17", "city": "Medan"},
    {"name": "KPP Pratama Medan Kota",                 "code": "KPP162","kanwil": "KW17", "city": "Medan"},
    {"name": "KPP Madya Medan",                        "code": "KPP163","kanwil": "KW17", "city": "Medan"},
    # Sumatera Selatan
    {"name": "KPP Pratama Palembang Ilir Barat",       "code": "KPP171","kanwil": "KW19", "city": "Palembang"},
    {"name": "KPP Madya Palembang",                    "code": "KPP172","kanwil": "KW19", "city": "Palembang"},
    # Riau
    {"name": "KPP Pratama Pekanbaru Senapelan",        "code": "KPP181","kanwil": "KW20", "city": "Pekanbaru"},
    {"name": "KPP Pratama Pekanbaru Tampan",           "code": "KPP182","kanwil": "KW20", "city": "Pekanbaru"},
    # Kalimantan Timur
    {"name": "KPP Pratama Balikpapan",                 "code": "KPP191","kanwil": "KW21", "city": "Balikpapan"},
    {"name": "KPP Pratama Samarinda Ulu",              "code": "KPP192","kanwil": "KW21", "city": "Samarinda"},
    # Sulawesi Selatan
    {"name": "KPP Pratama Makassar Utara",             "code": "KPP201","kanwil": "KW22", "city": "Makassar"},
    {"name": "KPP Pratama Makassar Selatan",           "code": "KPP202","kanwil": "KW22", "city": "Makassar"},
    {"name": "KPP Madya Makassar",                     "code": "KPP203","kanwil": "KW22", "city": "Makassar"},
    # Papua
    {"name": "KPP Pratama Jayapura",                   "code": "KPP211","kanwil": "KW23", "city": "Jayapura"},
    # Nusa Tenggara
    {"name": "KPP Pratama Kupang",                     "code": "KPP221","kanwil": "KW24", "city": "Kupang"},
]


def seed_geography_data(db: Session) -> dict:
    """Idempotent geography seed – skips if data already present."""
    if db.query(Kanwil).count() > 0:
        logger.info("Geography data already seeded – skipping.")
        return {"skipped": True}

    # --- Provinces ---
    prov_map: dict[str, Province] = {}
    for p in PROVINCES:
        obj = Province(name=p["name"], code=p["code"])
        db.add(obj)
        prov_map[p["name"]] = obj
    db.flush()

    # --- Cities ---
    city_map: dict[str, City] = {}
    for c in CITIES:
        prov = prov_map.get(c["province"])
        obj = City(name=c["name"], province_id=prov.id if prov else None,
                   lat=c.get("lat"), lon=c.get("lon"))
        db.add(obj)
        city_map[c["name"]] = obj
    db.flush()

    # --- Kanwil ---
    kanwil_map: dict[str, Kanwil] = {}
    for k in KANWILS:
        prov = prov_map.get(k["province"])
        obj = Kanwil(name=k["name"], code=k["code"],
                     province_id=prov.id if prov else None,
                     lat=k.get("lat"), lon=k.get("lon"))
        db.add(obj)
        kanwil_map[k["code"]] = obj
    db.flush()

    # --- KPP ---
    for kpp_data in KPPS:
        kanwil = kanwil_map.get(kpp_data["kanwil"])
        city = city_map.get(kpp_data["city"])
        lat = city.lat if city else None
        lon = city.lon if city else None
        obj = KPP(name=kpp_data["name"], code=kpp_data["code"],
                  kanwil_id=kanwil.id if kanwil else None,
                  city_id=city.id if city else None,
                  lat=lat, lon=lon)
        db.add(obj)

    db.commit()
    logger.info("Geography seed completed: %d provinces, %d cities, %d kanwil, %d kpp",
                len(PROVINCES), len(CITIES), len(KANWILS), len(KPPS))
    return {
        "provinces": len(PROVINCES),
        "cities": len(CITIES),
        "kanwils": len(KANWILS),
        "kpps": len(KPPS),
    }
