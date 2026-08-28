"""Single connection factory. Every database access in this project goes through get_connection().

Usage (in tools and ingest functions):

    from src.db.connection import get_connection

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    # connection is committed and closed on clean exit;
    # rolled back and closed on exception.
"""

import psycopg

from config import DB_URL


def get_connection() -> psycopg.Connection:
    """Open and return a new psycopg3 connection to the project database.

    Use exclusively as a context manager so the transaction is always resolved:

        with get_connection() as conn:
            conn.execute(...)
        # clean exit → commit + close
        # exception  → rollback + close

    For ingest functions that need to share a transaction, pass the connection
    in explicitly rather than calling get_connection() inside them — the caller
    controls commit/rollback.
    """
    return psycopg.connect(DB_URL)
