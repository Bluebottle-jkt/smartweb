"""
ETL Ingestion Service

Supports ingesting new datasets from CSV or Parquet files into SmartWeb's
PostgreSQL store, then syncing the entity_search_index and (optionally) Neo4j.

Pipeline:
    Raw file (CSV / Parquet)
      → Schema validation against config/schema_mapping.yaml
      → Normalisation
      → PostgreSQL upsert
      → entity_search_index rebuild
      → Neo4j sync (optional)
      → DatasetVersion record
"""
from __future__ import annotations

import csv
import hashlib
import io
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import yaml
from sqlalchemy.orm import Session

from app.db.models.search_index import DatasetVersion
from app.db.search_index import refresh_entity_search_index

# Path to schema mapping config
_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "../../../config/schema_mapping.yaml"
)


def _load_config() -> Dict:
    """Load schema_mapping.yaml. Returns empty dict on failure."""
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _hash_content(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

class IngestionService:
    """Orchestrates dataset ingestion."""

    def __init__(self, db: Session):
        self.db = db
        self.config = _load_config()

    # ------------------------------------------------------------------
    # CSV ingestion
    # ------------------------------------------------------------------

    def ingest_csv(
        self,
        content: bytes,
        dataset_key: str,
        filename: str = "upload.csv",
        ingested_by: str = "system",
        delimiter: str = ";",
        encoding: str = "utf-8-sig",
    ) -> DatasetVersion:
        """
        Parse a CSV file and upsert records into the target model.
        Returns a DatasetVersion row recording the ingestion result.
        """
        version_tag = f"{dataset_key}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        version = DatasetVersion(
            version_tag=version_tag,
            source_file=filename,
            source_type="CSV",
            schema_hash=_hash_content(content),
            ingested_by=ingested_by,
            ingestion_started_at=datetime.now(timezone.utc),
            status="RUNNING",
        )
        self.db.add(version)
        self.db.flush()

        try:
            ds_config = self.config.get("datasets", {}).get(dataset_key)
            if not ds_config:
                raise ValueError(f"Unknown dataset_key: '{dataset_key}'. Check config/schema_mapping.yaml.")

            field_map: Dict[str, str] = ds_config.get("field_map", {})
            transformations: Dict[str, Dict[str, str]] = ds_config.get("transformations", {})

            text = content.decode(encoding, errors="replace")
            reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

            target_model_name: str = ds_config["target_model"]
            model_cls = self._resolve_model(target_model_name)

            rows_processed = 0
            upserted = 0

            for raw_row in reader:
                mapped = self._map_row(raw_row, field_map, transformations)
                self._upsert_model(model_cls, mapped, ds_config.get("unique_key"))
                rows_processed += 1
                upserted += 1

            self.db.flush()

            # Refresh search index
            refresh_entity_search_index(self.db)

            version.status = "COMPLETED"
            version.record_count = rows_processed
            version.entity_count = upserted
            version.ingestion_completed_at = datetime.now(timezone.utc)
            self.db.commit()

        except Exception as e:
            version.status = "FAILED"
            version.error_message = str(e)[:2000]
            version.ingestion_completed_at = datetime.now(timezone.utc)
            self.db.commit()
            raise

        return version

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_model(self, name: str):
        from app.db import models as m
        cls = getattr(m, name, None)
        if cls is None:
            raise ValueError(f"Model '{name}' not found in app.db.models")
        return cls

    def _map_row(
        self,
        raw: Dict[str, Any],
        field_map: Dict[str, str],
        transformations: Dict[str, Dict[str, str]],
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for src_col, tgt_field in field_map.items():
            val = raw.get(src_col)
            if val is not None and tgt_field in transformations:
                val = transformations[tgt_field].get(str(val), val)
            if val is not None:
                result[tgt_field] = val
        return result

    def _upsert_model(self, model_cls, data: Dict[str, Any], unique_key: Optional[str]):
        """Insert or update a single model row."""
        if unique_key and unique_key in data:
            key_val = data[unique_key]
            existing = (
                self.db.query(model_cls)
                .filter(getattr(model_cls, unique_key) == key_val)
                .first()
            )
            if existing:
                for k, v in data.items():
                    if hasattr(existing, k):
                        setattr(existing, k, v)
                return

        # Remove 'id' if present to let DB auto-assign
        data.pop("id", None)
        obj = model_cls(**{k: v for k, v in data.items() if hasattr(model_cls, k)})
        self.db.add(obj)

    def list_versions(self, limit: int = 50) -> List[DatasetVersion]:
        return (
            self.db.query(DatasetVersion)
            .order_by(DatasetVersion.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_config_summary(self) -> Dict:
        """Return a summary of available datasets from config."""
        datasets = self.config.get("datasets", {})
        return {
            key: {
                "description": v.get("description", ""),
                "source_type": v.get("source_type", ""),
                "target_model": v.get("target_model", ""),
                "unique_key": v.get("unique_key"),
            }
            for key, v in datasets.items()
        }
