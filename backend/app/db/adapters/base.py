"""
Abstract base class for all Source DB adapters.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List, Optional


class SourceAdapter(ABC):
    """
    Vendor-neutral read-only interface to an external data source.

    Each concrete adapter handles connection pooling, parameter binding,
    and result serialisation for a specific database engine.
    """

    def __init__(self, connection_string: str, **kwargs: Any):
        self.connection_string = connection_string
        self.options = kwargs
        self._connect()

    # ------------------------------------------------------------------
    # Connection lifecycle (implement in subclass)
    # ------------------------------------------------------------------

    @abstractmethod
    def _connect(self) -> None:
        """Initialise the connection / engine."""

    def close(self) -> None:
        """Release resources. Override if needed."""

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # ------------------------------------------------------------------
    # Query interface
    # ------------------------------------------------------------------

    @abstractmethod
    def query(
        self,
        sql: str,
        params: Optional[List[Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a read-only SQL statement and return rows as dicts.

        Args:
            sql:    Raw SQL string; use ? (or %s for psycopg2) for params.
            params: Positional parameter list matching placeholders.

        Returns:
            List of row dicts keyed by column name (lower-cased).
        """

    def query_iter(
        self,
        sql: str,
        params: Optional[List[Any]] = None,
        chunk_size: int = 1000,
    ) -> Iterator[List[Dict[str, Any]]]:
        """
        Stream large result sets in chunks.
        Default implementation loads all rows then yields in chunks.
        Override for true server-side cursor streaming.
        """
        rows = self.query(sql, params)
        for i in range(0, len(rows), chunk_size):
            yield rows[i : i + chunk_size]

    # ------------------------------------------------------------------
    # Introspection helpers (optional, override for richer support)
    # ------------------------------------------------------------------

    def list_tables(self) -> List[str]:
        """Return table names in the connected database/schema."""
        raise NotImplementedError

    def describe_table(self, table_name: str) -> List[Dict[str, str]]:
        """Return column metadata: [{name, type, nullable}, ...]."""
        raise NotImplementedError

    def test_connection(self) -> bool:
        """Return True if the connection is alive."""
        try:
            self.query("SELECT 1")
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def vendor(self) -> str:
        """Human-readable vendor name, e.g. 'postgresql'."""
