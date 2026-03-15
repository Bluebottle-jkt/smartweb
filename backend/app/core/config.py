from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://smartweb:smartweb_dev_pass@localhost:5432/smartweb_db"

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production-min-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Seed configuration
    ALLOW_DB_RESET: bool = False
    AUTO_SEED: bool = False
    SEED_GROUPS: int = 100
    SEED_TAXPAYERS: int = 1500
    SEED_BOS: int = 300
    SEED_RNG: int = 20260109

    # Derived groups configuration
    ALLOW_DERIVE: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"

    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "SmartWeb - Wajib Pajak Grup"

    # Neo4j configuration
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "smartweb_neo4j_pass"
    NEO4J_ENABLED: bool = False  # Feature flag – safe default

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
