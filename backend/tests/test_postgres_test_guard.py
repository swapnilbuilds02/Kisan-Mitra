"""Database safety gates fail before a network connection is attempted."""

from types import SimpleNamespace

import pytest

from backend.tests.postgres_test_guard import require_disposable_database


def fake_driver(dbname, host):
    def no_connect(*args, **kwargs):
        raise AssertionError("Unsafe target must not be connected")
    return SimpleNamespace(
        conninfo=SimpleNamespace(conninfo_to_dict=lambda dsn: {"dbname": dbname, "host": host}),
        connect=no_connect,
    )


def test_database_tests_need_explicit_opt_in(monkeypatch):
    monkeypatch.setenv("KM_TEST_DATABASE_URL", "postgresql://localhost/km_test_example")
    monkeypatch.delenv("KM_ALLOW_DISPOSABLE_DB_TESTS", raising=False)
    with pytest.raises(AssertionError, match="opt-in"):
        require_disposable_database(fake_driver("km_test_example", "localhost"))


@pytest.mark.parametrize("dbname,host", [
    ("production", "localhost"),
    ("km_test_example", "db.production.example"),
])
def test_database_tests_refuse_unsafe_targets_before_connect(monkeypatch, dbname, host):
    monkeypatch.setenv("KM_TEST_DATABASE_URL", "postgresql://placeholder")
    monkeypatch.setenv("KM_ALLOW_DISPOSABLE_DB_TESTS", "YES")
    with pytest.raises(AssertionError):
        require_disposable_database(fake_driver(dbname, host))
