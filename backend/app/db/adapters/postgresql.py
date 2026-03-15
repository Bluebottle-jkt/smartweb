"""
PostgreSQL adapter – uses psycopg2 directly for read-only source queries.
(Not to be confused with the main SQLAlchemy ORM session.)
"""
from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional

from app.db.adapters.base import SourceAdapter


class PostgreSQLAdapter(SourceAdapter):
    """Read-only adapter for a PostgreSQL source database."""

    @property
    def vendor(self) -> str:
        return "postgresql"

    def _connect(self) -> None:
        try:
            import psycopg2
            import psycopg2.extras
            self._conn = psycopg2.connect(self.connection_string)
            self._conn.set_session(readonly=True, autocommit=True)
            self._extras = psycopg2.extras
        except ImportError:
            raise RuntimeError("psycopg2 is required for the PostgreSQL adapter. Install it with: pip install psycopg2-binary")

    def close(self) -> None:
        if hasattr(self, "_conn") and self._conn:
            self._conn.close()

    def query(self, sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        with self._conn.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
            cur.execute(sql, params or [])
            return [dict(row) for row in cur.fetchall()]

    def query_iter(
        self,
        sql: str,
        params: Optional[List[Any]] = None,
        chunk_size: int = 1000,
    ) -> Iterator[List[Dict[str, Any]]]:
        """Uses a server-side named cursor for true streaming."""
        with self._conn.cursor(
            name="smartweb_src_cursor",
            cursor_factory=self._extras.RealDictCursor,
            withhold=True,
        ) as cur:
            cur.execute(sql, params or [])
            while True:
                rows = cur.fetchmany(chunk_size)
                if not rows:
                    break
                yield [dict(r) for r in rows]

    def list_tables(self) -> List[str]:
        rows = self.query(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        )
        return [r["table_name"] for r in rows]

    def describe_table(self, table_name: str) -> List[Dict[str, str]]:
        rows = self.query(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s ORDER BY ordinal_position",
            [table_name],
        )
        return [{"name": r["column_name"], "type": r["data_type"], "nullable": r["is_nullable"]} for r in rows]
