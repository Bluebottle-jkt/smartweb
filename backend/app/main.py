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
    network
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    setup_logging(settings.LOG_LEVEL)

    # Auto-seed if enabled and database is empty
    if settings.AUTO_SEED:
        db = SessionLocal()
        try:
            count = db.query(Group).count()
            if count == 0:
                print("Database is empty. Running auto-seed...")
                from app.db.seed import generate_seed_data
                generate_seed_data(db)
                print("Auto-seed completed.")
        except Exception as e:
            print(f"Auto-seed failed: {e}")
        finally:
            db.close()

    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="API for Wajib Pajak Grup Task Force 2026",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3100", "http://127.0.0.1:3000", "http://127.0.0.1:3100", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(search.router)
app.include_router(groups.router)
app.include_router(taxpayers.router)
app.include_router(beneficial_owners.router)
app.include_router(exports.router)
app.include_router(admin.router)
app.include_router(derived_groups.router)
app.include_router(network.router)


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "SmartWeb API - Wajib Pajak Grup Task Force",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
