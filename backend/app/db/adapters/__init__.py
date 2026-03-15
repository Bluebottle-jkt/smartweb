"""
Source Database Adapter Layer

Provides a vendor-neutral interface for reading source data from
PostgreSQL, SQL Server, Oracle, or MySQL.  The canonical write store
is always PostgreSQL (via SQLAlchemy ORM); these adapters are for
*reading* external/legacy source databases.

Usage:
    from app.db.adapters import get_adapter
    adapter = get_adapter("sqlserver", connection_string="mssql+pyodbc://...")
    rows = adapter.query("SELECT * FROM WP_DATA WHERE TAHUN = ?", [2025])
"""

from app.db.adapters.base import SourceAdapter
from app.db.adapters.registry import get_adapter, list_supported_vendors

__all__ = ["SourceAdapter", "get_adapter", "list_supported_vendors"]
