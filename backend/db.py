# backend/backend/db.py
import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

DB_USER = os.environ.get("DB_USER", "vento")
DB_PASS = os.environ.get("DB_PASS", "")
DB_NAME = os.environ.get("DB_NAME", "vento")
INSTANCE_CONNECTION_NAME = os.environ.get("INSTANCE_CONNECTION_NAME", "")  # PROJECT:REGION:INSTANCE

def get_engine() -> Engine:
    """
    Prefer UNIX socket (Cloud Run + Cloud SQL connection).
    If DB_HOST provided, we fall back to TCP.
    """
    db_host = os.environ.get("DB_HOST")  # optional TCP host (public IP)
    if db_host:
        # TCP connection (useful for local dev or if public IP set)
        url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{db_host}/{DB_NAME}"
    elif INSTANCE_CONNECTION_NAME:
        # connect via unix socket path
        # SQLAlchemy + psycopg2 can connect with host=/cloudsql/INSTANCE_NAME
        host = f"/cloudsql/{INSTANCE_CONNECTION_NAME}"
        url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@localhost/{DB_NAME}"
        engine = create_engine(url, connect_args={"host": host})
        return engine
    else:
        raise RuntimeError("No DB_HOST or INSTANCE_CONNECTION_NAME provided to db.py")

    engine = create_engine(url)
    return engine
