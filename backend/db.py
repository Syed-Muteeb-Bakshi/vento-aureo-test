# backend/db.py
import os
from google.cloud.sql.connector import Connector, IPTypes
from sqlalchemy import text, create_engine
from sqlalchemy.pool import NullPool

# Config from env (set in Cloud Run)
INSTANCE_CONNECTION_NAME = os.environ.get(
    "INSTANCE_CONNECTION_NAME", "just-smithy-479012-a1:us-east1:vento-postgres"
)
DB_USER = os.environ.get("DB_USER", "giorno_geovanna")
DB_PASS = os.environ.get("DB_PASS", "")
DB_NAME = os.environ.get("DB_NAME", "gold_experience")

_connector = None
_engine = None

def _init_connector():
    global _connector
    if _connector is None:
        # Use PUBLIC IP for simplicity (IPTypes.PUBLIC) — fine for Cloud Run + Cloud SQL
        _connector = Connector(ip_type=IPTypes.PUBLIC)
    return _connector

def get_raw_connection():
    """
    Return a raw DB connection object (pg8000) for legacy code that expects a cursor.
    """
    conn = _init_connector().connect(
        INSTANCE_CONNECTION_NAME,
        "pg8000",
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME,
    )
    return conn

def get_engine():
    """
    Return a SQLAlchemy Engine that uses the Cloud SQL Connector to create the
    underlying DB connection. Uses NullPool to avoid pooled sockets in Cloud Run.
    """
    global _engine
    if _engine is None:
        # create_engine with a creator that uses the connector
        def creator():
            return _init_connector().connect(
                INSTANCE_CONNECTION_NAME,
                "pg8000",
                user=DB_USER,
                password=DB_PASS,
                db=DB_NAME,
            )
        # dialect 'postgresql+pg8000' with a creator function
        _engine = create_engine("postgresql+pg8000://", creator=creator, poolclass=NullPool)
    return _engine

def get_db_connection():
    """
    Return a SQLAlchemy Connection object (use .execute/text for queries).
    Caller should close() when done.
    """
    return get_engine().connect()

# convenience helper used by routes
def execute_text(sql, params=None):
    with get_db_connection() as conn:
        return conn.execute(text(sql), params or {})
