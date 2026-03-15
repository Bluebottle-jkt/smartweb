"""
Adapter registry – maps vendor names to adapter classes.

Usage:
    from app.db.adapters import get_adapter

    adapter = get_adapter("sqlserver", connection_string="mssql+pyodbc://...")
    rows = adapter.query("SELECT TOP 100 * FROM WP_DATA")
"""
from __future__ import annotations

from typing import Any, List

from app.db.adapters.base import SourceAdapter

_REGISTRY: dict[str, str] = {
    "postgresql": "app.db.adapters.postgresql.PostgreSQLAdapter",
    "postgres": "app.db.adapters.postgresql.PostgreSQLAdapter",
    "sqlserver": "app.db.adapters.sqlserver.SQLServerAdapter",
    "mssql": "app.db.adapters.sqlserver.SQLServerAdapter",
    "oracle": "app.db.adapters.oracle.OracleAdapter",
    "mysql": "app.db.adapters.mysql.MySQLAdapter",
    "mariadb": "app.db.adapters.mysql.MySQLAdapter",
}


def list_supported_vendors() -> List[str]:
    """Return list of supported vendor names."""
    return sorted(set(_REGISTRY.keys()))


def get_adapter(vendor: str, connection_string: str, **kwargs: Any) -> SourceAdapter:
    """
    Instantiate and return the correct SourceAdapter for the given vendor.

    Args:
        vendor:            One of 'postgresql', 'sqlserver', 'oracle', 'mysql', etc.
        connection_string: Vendor-appropriate connection string.
        **kwargs:          Extra options forwarded to the adapter constructor.

    Raises:
        ValueError: If the vendor is not supported.
        RuntimeError: If the required driver package is not installed.
    """
    key = vendor.lower().strip()
    cls_path = _REGISTRY.get(key)
    if not cls_path:
        supported = ", ".join(list_supported_vendors())
        raise ValueError(
            f"Unsupported vendor '{vendor}'. Supported: {supported}"
        )

    module_path, cls_name = cls_path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    cls = getattr(module, cls_name)
    return cls(connection_string=connection_string, **kwargs)
