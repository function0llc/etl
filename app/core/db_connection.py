from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
from urllib.parse import quote_plus

import keyring
from sqlalchemy import Engine, create_engine, text

from app.core.models import ConnectionProfile


SERVICE_NAME = "etl-loader-postgres"


def password_key(profile_name: str, username: str, host: str, database: str) -> str:
    return f"{profile_name}:{username}@{host}/{database}"


def save_password(profile: ConnectionProfile, password: str) -> ConnectionProfile:
    key = profile.password_key or password_key(profile.name, profile.username, profile.host, profile.database)
    keyring.set_password(SERVICE_NAME, key, password)
    profile.password_key = key
    return profile


def get_password(profile: ConnectionProfile) -> str | None:
    if not profile.password_key:
        return None
    return keyring.get_password(SERVICE_NAME, profile.password_key)


def build_url(profile: ConnectionProfile, password: str | None = None) -> str:
    pwd = quote_plus(password or "")
    ssl = f"?sslmode={quote_plus(profile.ssl_mode)}" if profile.ssl_mode else ""
    return f"postgresql+psycopg://{quote_plus(profile.username)}:{pwd}@{quote_plus(profile.host)}:{profile.port}/{quote_plus(profile.database)}{ssl}"


def create_postgres_engine(profile: ConnectionProfile, password: str | None = None) -> Engine:
    return create_engine(build_url(profile, password if password is not None else get_password(profile)), future=True)


def test_connection(profile: ConnectionProfile, password: str | None = None) -> tuple[bool, str]:
    try:
        engine = create_postgres_engine(profile, password)
        with engine.connect() as conn:
            conn.execute(text("select 1"))
        engine.dispose()
        return True, "Connection successful"
    except Exception as exc:  # UI diagnostic only; URL/password are never included.
        return False, type(exc).__name__


@contextmanager
def db_engine(profile: ConnectionProfile, password: str | None = None) -> Iterator[Engine]:
    engine = create_postgres_engine(profile, password)
    try:
        yield engine
    finally:
        engine.dispose()
