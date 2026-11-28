"""Disposable PostgreSQL verification for additive password storage and grants."""

from pathlib import Path
from uuid import uuid4

import pytest

psycopg = pytest.importorskip('psycopg')
from backend.tests.postgres_test_guard import require_disposable_database
from backend.app.credentials import PostgresCredentialStore
from backend.app.identity import PostgresIdentityStore
from backend.app.passwords import verify_password


def test_password_migration_and_private_credentials():
    dsn = require_disposable_database(psycopg)
    migrations = Path(__file__).resolve().parents[1] / 'migrations'
    subject = uuid4()
    with psycopg.connect(dsn, autocommit=True) as connection:
        with connection.cursor() as cursor:
            assert cursor.execute("SELECT to_regclass('public.users')").fetchone() == (None,)
            for number in ('0001_identity_foundation', '0002_auth_state', '0003_farmer_identity', '0004_password_credentials'):
                cursor.execute((migrations / f'{number}.up.sql').read_text(encoding='utf-8'))
            try:
                cursor.execute("INSERT INTO users(id,mobile_number,role,account_state,is_verified) VALUES (%s,'9876543210','farmer','active',TRUE)", (subject,))
                store = PostgresCredentialStore(PostgresIdentityStore(dsn), 'test-pepper-value-that-is-at-least-32-bytes')
                assert store.create_internal(subject, 'CorrectHorse1234')
                assert verify_password('CorrectHorse1234', store.password_hash(subject))
                with pytest.raises(psycopg.errors.UniqueViolation):
                    store.create_internal(subject, 'AnotherPassword1234')
                assert store.replace_internal(subject, 'AnotherPassword1234')
                assert not verify_password('CorrectHorse1234', store.password_hash(subject))
                cursor.execute('GRANT km_api TO CURRENT_USER')
                cursor.execute('SET ROLE km_api')
                try:
                    with pytest.raises(psycopg.errors.InsufficientPrivilege):
                        cursor.execute('SELECT * FROM km_private.password_credentials')
                    with pytest.raises(psycopg.errors.InsufficientPrivilege):
                        cursor.execute("SELECT km_private.set_password_credential(%s,'bad',TRUE)", (subject,))
                finally:
                    cursor.execute('RESET ROLE')
                    cursor.execute('REVOKE km_api FROM CURRENT_USER')
            finally:
                cursor.execute('RESET ROLE')
                for number in ('0004_password_credentials', '0003_farmer_identity', '0002_auth_state', '0001_identity_foundation'):
                    cursor.execute((migrations / f'{number}.down.sql').read_text(encoding='utf-8'))
