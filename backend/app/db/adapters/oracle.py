"""
Oracle adapter – uses cx_Oracle (or oracledb, the newer drop-in).

Install: pip install oracledb
Connection string format:
  oracle+cx_oracle://user:pass@host:1521/?service_name=ORCL
  or raw Oracle Easy Connect:
  user/pass@host:1521/service_name
"""
from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional

from app.db.adapters.base import SourceAdapter


class OracleAdapter(SourceAdapter):
    """Read-only adapter for Oracle Database."""

    @property
    def vendor(self) -> str:
        return "oracle"

    def _connect(self) -> None:
        try:
            import oracledb as cx_Oracle
        except ImportError:
            try:
                import cx_Oracle
            except ImportError:
                raise RuntimeError(
                    "oracledb (or cx_Oracle) is required. Install with: pip install oracledb"
                )

        self._cx = cx_Oracle

        cs = self.connection_string
        # Strip SQLAlchemy prefix if present
        for prefix in ("oracle+cx_oracle://", "oracle+oracledb://"):
            if cs.startswith(prefix):
                cs = cs.replace(prefix, "", 1)
                break

        # cx_Oracle.connect accepts: user/pass@dsn
        self._conn = self._cx.connect(cs)

    def close(self) -> None:
        if hasattr(self, "_conn") and self._conn:
            self._conn.close()

    def _row_to_dict(self, cursor, row) -> Dict[str, Any]:
        columns = [d[0].lower() for d in cursor.description]
        return dict(zip(columns, row))

    def query(self, sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        cursor = self._conn.cursor()
        cursor.execute(sql, params or [])
        rows = cursor.fetchall()
        return [self._row_to_dict(cursor, r) for r in rows]

    def query_iter(
        self,
        sql: str,
        params: Optional[List[Any]] = None,
        chunk_size: int = 1000,
    ) -> Iterator[List[Dict[str, Any]]]:
        cursor = self._conn.cursor()
        cursor.arraysize = chunk_size
        cursor.execute(sql, params or [])
        while True:
            rows = cursor.fetchmany(chunk_size)
            if not rows:
                break
            yield [self._row_to_dict(cursor, r) for r in rows]

    def list_tables(self) -> List[str]:
        rows = self.query("SELECT TABLE_NAME FROM USER_TABLES ORDER BY TABLE_NAME")
        return [r["table_name"] for r in rows]

    def describe_table(self, table_name: str) -> List[Dict[str, str]]:
        rows = self.query(
            "SELECT COLUMN_NAME, DATA_TYPE, NULLABLE FROM USER_TAB_COLUMNS "
            "WHERE TABLE_NAME = :1 ORDER BY COLUMN_ID",
            [table_name.upper()],
        )
        return [{"name": r["column_name"], "type": r["data_type"], "nullable": r["nullable"]} for r in rows]
