from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import SessionLocal
from app.db.models import Group
from app.api.routers import (
    auth,
    search,
    groups,
    taxpayers,
    beneficial_owners,
    exports,
    admin,
    derived_groups,
    network,
)
from app.api.routers import entities, group_map, statistics, assistant, relationships
from app.core.rate_limit import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    setup_logging(settings.LOG_LEVEL)

    # ── Step 1: Auto-apply pending Alembic migrations ──────────────────────
    try:
        from alembic.config import Config
        from alembic import command as alembic_command
        import os
        # Resolve alembic.ini: CWD is backend/ when running via Docker/uvicorn
        ini_candidates = [
            "alembic.ini",
            os.path.join(os.path.dirname(__file__), "../../alembic.ini"),
        ]
        ini_path = next((p for p in ini_candidates if os.path.exists(p)), None)
        if ini_path:
            alembic_cfg = Config(ini_path)
            alembic_command.upgrade(alembic_cfg, "head")
            print("✓ Database migrations up-to-date.")
        else:
            print("⚠ alembic.ini not found – skipping auto-migration.")
    except Exception as e:
        print(f"⚠ Migration warning (non-fatal): {e}")

    # ── Step 2: Seed data ───────────────────────────────────────────────────
    if settings.AUTO_SEED:
        db = SessionLocal()
        try:
            count = db.query(Group).count()
            if count == 0:
                print("Database is empty. Running auto-seed...")
                from app.db.seed import generate_seed_data
                generate_seed_data(db)
                print("Auto-seed completed.")

            # Seed geography reference data (idempotent)
            from app.db.models.geography import Kanwil
            if db.query(Kanwil).count() == 0:
                print("Seeding geography data...")
                from app.db.seed_geography import seed_geography_data
                result = seed_geography_data(db)
                print(f"Geography seed completed: {result}")

            # Rebuild entity search index
            try:
                from app.db.search_index import refresh_entity_search_index
                refresh_entity_search_index(db)
                print("✓ Entity search index refreshed.")
            except Exception as idx_err:
                print(f"⚠ Search index refresh skipped: {idx_err}")

        except Exception as e:
            print(f"Startup seed failed: {e}")
        finally:
            db.close()

    yield

    from app.db.neo4j import close_driver
    close_driver()
    print("Shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.0.0",
    description="Graph Intelligence Platform – Wajib Pajak Grup Task Force 2026",
    lifespan=lifespan,
)

app.add_middleware(RateLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3100",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3100",
        "http://frontend:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core routers
app.include_router(auth.router)
app.include_router(search.router)
app.include_router(groups.router)
app.include_router(taxpayers.router)
app.include_router(beneficial_owners.router)
app.include_router(exports.router)
app.include_router(admin.router)
app.include_router(derived_groups.router)
app.include_router(network.router)

# Graph Intelligence v2 routers
app.include_router(entities.router)
app.include_router(group_map.router)
app.include_router(statistics.router)
app.include_router(assistant.router)
app.include_router(relationships.router)


@app.get("/")
def root():
    return {
        "message": "SmartWeb Graph Intelligence Platform",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
