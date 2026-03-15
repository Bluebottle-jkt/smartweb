"""
Neo4j connection utility for SmartWeb Graph Intelligence Platform.

Provides a driver singleton with graceful degradation when Neo4j is unavailable
or the NEO4J_ENABLED feature flag is off.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_driver = None


def get_driver():
    """Return the Neo4j driver singleton, initialised lazily."""
    global _driver
    if _driver is not None:
        return _driver

    if not settings.NEO4J_ENABLED:
        return None

    try:
        from neo4j import GraphDatabase  # type: ignore
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
        _driver.verify_connectivity()
        logger.info("Neo4j connected at %s", settings.NEO4J_URI)
    except Exception as exc:
        logger.warning("Neo4j unavailable (%s) – graph intelligence will use PostgreSQL fallback.", exc)
        _driver = None

    return _driver


def is_neo4j_available() -> bool:
    return get_driver() is not None


@contextmanager
def neo4j_session() -> Generator:
    """Context manager that yields a Neo4j session or raises RuntimeError."""
    driver = get_driver()
    if driver is None:
        raise RuntimeError("Neo4j is not available")
    with driver.session() as session:
        yield session


def close_driver() -> None:
    """Cleanly close the driver (called on app shutdown)."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
        logger.info("Neo4j driver closed.")


# ---------------------------------------------------------------------------
# Utility: run a Cypher query and return results as a list of dicts
# ---------------------------------------------------------------------------

def run_query(cypher: str, parameters: Optional[dict] = None) -> list[dict]:
    """Execute a read-only Cypher query and return rows as plain dicts."""
    driver = get_driver()
    if driver is None:
        return []
    with driver.session() as session:
        result = session.run(cypher, parameters or {})
        return [record.data() for record in result]


def run_write(cypher: str, parameters: Optional[dict] = None) -> list[dict]:
    """Execute a write Cypher query and return rows as plain dicts."""
    driver = get_driver()
    if driver is None:
        return []
    with driver.session() as session:
        result = session.run(cypher, parameters or {})
        return [record.data() for record in result]
