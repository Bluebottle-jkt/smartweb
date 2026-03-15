"""
MySQL / MariaDB adapter – uses PyMySQL (pure Python, no C dependency).

Install: pip install pymysql
Connection string format:
  mysql+pymysql://user:pass@host:3306/dbname
  or raw PyMySQL kwargs via connection_string as JSON:
  {"host":"...", "user":"...", "password":"...", "database":"..."}
"""
from __future__ import annotations

import json
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urlparse

from app.db.adapters.base import SourceAdapter


def _parse_url(cs: str) -> Dict[str, Any]:
    """Parse a mysql+pymysql:// URL into pymysql.connect kwargs."""
    if cs.startswith("{"):
        return json.loads(cs)

    for prefix in ("mysql+pymysql://", "mysql://", "mariadb+pymysql://", "mariadb://"):
        cs = cs.replace(prefix, "mysql://", 1)

    parsed = urlparse(cs)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": parsed.username,
        "password": parsed.password or "",
        "database": parsed.path.lstrip("/"),
        "charset": "utf8mb4",
        "cursorclass": None,  # set later
    }


class MySQLAdapter(SourceAdapter):
    """Read-only adapter for MySQL / MariaDB."""

    @property
    def vendor(self) -> str:
        return "mysql"

    def _connect(self) -> None:
        try:
            import pymysql
            import pymysql.cursors
        except ImportError:
            raise RuntimeError("pymysql is required. Install with: pip install pymysql")

        self._pymysql = pymysql
        kwargs = _parse_url(self.connection_string)
        kwargs["cursorclass"] = pymysql.cursors.DictCursor
        self._conn = pymysql.connect(**kwargs)

    def close(self) -> None:
        if hasattr(self, "_conn") and self._conn:
            self._conn.close()

    def query(self, sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        with self._conn.cursor() as cur:
            cur.execute(sql, params or [])
            rows = cur.fetchall()
            return [{k.lower(): v for k, v in row.items()} for row in rows]

    def query_iter(
        self,
        sql: str,
        params: Optional[List[Any]] = None,
        chunk_size: int = 1000,
    ) -> Iterator[List[Dict[str, Any]]]:
        with self._conn.cursor() as cur:
            cur.execute(sql, params or [])
            while True:
                rows = cur.fetchmany(chunk_size)
                if not rows:
                    break
                yield [{k.lower(): v for k, v in row.items()} for row in rows]

    def list_tables(self) -> List[str]:
        rows = self.query("SHOW TABLES")
        return [list(r.values())[0] for r in rows]

    def describe_table(self, table_name: str) -> List[Dict[str, str]]:
        rows = self.query(f"DESCRIBE `{table_name}`")
        return [{"name": r["field"], "type": r["type"], "nullable": r.get("null", "YES")} for r in rows]
