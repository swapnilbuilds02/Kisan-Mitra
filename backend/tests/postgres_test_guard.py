"""Reject shared or unmarked PostgreSQL servers before destructive test setup."""

import os

import pytest

MARKER = "KISAN_MITRA_DISPOSABLE_TEST_ONLY"


def require_disposable_database(psycopg):
    dsn = os.getenv("KM_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("KM_TEST_DATABASE_URL is not set")
    assert os.getenv("KM_ALLOW_DISPOSABLE_DB_TESTS") == "YES", "Explicit disposable database opt-in is required"
    options = psycopg.conninfo.conninfo_to_dict(dsn)
    assert options.get("dbname", "").startswith("km_test_"), "Refusing a non-test database"
    assert options.get("host", "localhost") in ("localhost", "127.0.0.1", "::1"), "Refusing a non-local database"
    with psycopg.connect(dsn, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT shobj_description(oid, 'pg_database') FROM pg_database WHERE datname=current_database()")
            assert cursor.fetchone() == (MARKER,), "Database lacks disposable test marker"
            cursor.execute("SELECT datname FROM pg_database WHERE NOT datistemplate")
            databases = {name for (name,) in cursor.fetchall()}
            assert databases <= {"postgres", options["dbname"]}, "Refusing a shared PostgreSQL cluster"
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname='km_api'")
            assert cursor.fetchone() is None, "km_api role already exists on this server"
    return dsn
