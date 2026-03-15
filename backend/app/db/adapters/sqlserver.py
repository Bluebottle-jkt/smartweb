"""
SQL Server adapter – uses pyodbc.

Install: pip install pyodbc
Connection string format:
  mssql+pyodbc://user:pass@host/db?driver=ODBC+Driver+17+for+SQL+Server
  or raw pyodbc DSN:
  DRIVER={ODBC Driver 17 for SQL Server};SERVER=host;DATABASE=db;UID=u;PWD=p
"""
from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional

from app.db.adapters.base import SourceAdapter


def _to_pyodbc_dsn(cs: str) -> str:
    """Convert SQLAlchemy-style URL to pyodbc DSN if needed."""
    if cs.startswith("mssql+pyodbc://"):
        # Strip the mssql+pyodbc:// prefix – pass the remainder as-is to pyodbc
        return cs.replace("mssql+pyodbc://", "", 1)
    return cs  # assume raw pyodbc DSN


class SQLServerAdapter(SourceAdapter):
    """Read-only adapter for Microsoft SQL Server / Azure SQL."""

    @property
    def vendor(self) -> str:
        return "sqlserver"

    def _connect(self) -> None:
        try:
            import pyodbc
        except ImportError:
            raise RuntimeError("pyodbc is required. Install with: pip install pyodbc")

        dsn = _to_pyodbc_dsn(self.connection_string)
        self._conn = pyodbc.connect(dsn, readonly=True)
        self._conn.autocommit = True

    def close(self) -> None:
        if hasattr(self, "_conn") and self._conn:
            self._conn.close()

    def _row_to_dict(self, cursor, row) -> Dict[str, Any]:
        columns = [col[0].lower() for col in cursor.description]
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
        cursor.execute(sql, params or [])
        while True:
            rows = cursor.fetchmany(chunk_size)
            if not rows:
                break
            yield [self._row_to_dict(cursor, r) for r in rows]

    def list_tables(self) -> List[str]:
        rows = self.query(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME"
        )
        return [r["table_name"] for r in rows]

    def describe_table(self, table_name: str) -> List[Dict[str, str]]:
        rows = self.query(
            "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION",
            [table_name],
        )
        return [{"name": r["column_name"], "type": r["data_type"], "nullable": r["is_nullable"]} for r in rows]
