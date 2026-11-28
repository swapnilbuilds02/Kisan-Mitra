"""Guarded disposable-database verification of restricted Admin provisioning.

This test runs last in CI. The CI PostgreSQL service is destroyed afterwards;
manual runs must delete the marked disposable database after inspection.
"""

from pathlib import Path

import pytest

psycopg = pytest.importorskip('psycopg')
from backend.tests.postgres_test_guard import require_disposable_database


def test_admin_provisioning_activation_and_runtime_permissions():
    dsn = require_disposable_database(psycopg)
    migrations = Path(__file__).resolve().parents[1] / 'migrations'
    names = ('identity_foundation', 'auth_state', 'farmer_identity', 'password_credentials',
             'otp_recovery', 'farmer_onboarding', 'partner_applications', 'admin_identity')
    with psycopg.connect(dsn, autocommit=True) as connection:
        with connection.cursor() as cursor:
            assert cursor.execute("SELECT to_regclass('public.users')").fetchone() == (None,)
            for number, name in enumerate(names, 1):
                cursor.execute((migrations / f'{number:04d}_{name}.up.sql').read_text(encoding='utf-8'))
            assert cursor.execute("SELECT to_regclass('km_private.admin_provisioning')").fetchone()[0]
            outcomes = [cursor.execute('SELECT km_private.admin_auth_attempt(%s,%s,%s)',
                        ('1'*64,'2'*64,'password')).fetchone()[0] for _ in range(4)]
            assert outcomes == [True,True,True,False]
            subject = cursor.execute('SELECT km_private.prepare_admin(%s,%s,%s,%s)',
                                     ('9876543210', 'Test Owner', None, True)).fetchone()[0]
            assert subject
            assert cursor.execute('SELECT km_private.prepare_admin(%s,%s,%s,%s)',
                                  ('9876543210', 'Duplicate', None, True)).fetchone() == (None,)
            assert cursor.execute('SELECT km_private.admin_active(%s)', (subject,)).fetchone() == (False,)
            challenge = cursor.execute('SELECT km_private.issue_purpose_otp(%s,%s,%s,%s,%s,%s)',
                                       ('9876543210', 'a'*64, 'b'*64, 'c'*64, 'ACCOUNT_CLAIM', subject)).fetchone()[0]
            assert challenge
            assert cursor.execute('SELECT km_private.consume_admin_verification_otp(%s,%s,%s,%s)',
                                  (challenge, '9876543210', 'c'*64, 'd'*64)).fetchone() == (True,)
            assert cursor.execute('SELECT km_private.consume_admin_verification_otp(%s,%s,%s,%s)',
                                  (challenge, '9876543210', 'c'*64, 'e'*64)).fetchone() == (False,)
            encoded = 'scrypt$16384$8$1$' + 'A'*24 + '$' + 'B'*44
            assert cursor.execute('SELECT km_private.activate_admin(%s,%s)', ('d'*64, encoded)).fetchone() == (True,)
            assert cursor.execute('SELECT km_private.activate_admin(%s,%s)', ('d'*64, encoded)).fetchone() == (False,)
            assert cursor.execute('SELECT km_private.admin_active(%s)', (subject,)).fetchone() == (True,)
            session = cursor.execute('SELECT km_private.create_password_session(%s,%s,%s,%s)',
                                     (subject, 'f'*64, 600, encoded)).fetchone()[0]
            assert session
            cursor.execute('GRANT km_api TO CURRENT_USER')
            cursor.execute('SET ROLE km_api')
            try:
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cursor.execute('SELECT * FROM km_private.admin_provisioning')
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cursor.execute('SELECT km_private.prepare_admin(%s,%s,%s,%s)',
                                   ('9876543211', 'Unauthorized', subject, False))
            finally:
                cursor.execute('RESET ROLE')
                cursor.execute('REVOKE km_api FROM CURRENT_USER')
