"""Guarded database checks for purpose isolation and atomic reset."""

from pathlib import Path
from uuid import uuid4

import pytest

psycopg = pytest.importorskip('psycopg')
from backend.tests.postgres_test_guard import require_disposable_database


def test_recovery_migration_and_purpose_boundary():
    dsn = require_disposable_database(psycopg)
    migrations = Path(__file__).resolve().parents[1] / 'migrations'
    user_id = uuid4()
    mobile = '9876543210'
    digest = 'a' * 64
    with psycopg.connect(dsn, autocommit=True) as connection:
        with connection.cursor() as cursor:
            assert cursor.execute("SELECT to_regclass('public.users')").fetchone() == (None,)
            for number in range(1, 6):
                name = {1:'identity_foundation', 2:'auth_state', 3:'farmer_identity',
                    4:'password_credentials', 5:'otp_recovery'}[number]
                cursor.execute((migrations / f'{number:04d}_{name}.up.sql').read_text(encoding='utf-8'))
            try:
                cursor.execute("INSERT INTO users(id,mobile_number,role,account_state,is_verified) VALUES (%s,%s,'farmer','active',TRUE)", (user_id, mobile))
                cursor.execute("INSERT INTO km_private.password_credentials(user_id,password_hash) VALUES (%s,%s)",
                    (user_id, 'scrypt$16384$8$1$'+'A'*24+'$'+'B'*44))
                cursor.execute('SELECT km_private.issue_purpose_otp(%s,%s,%s,%s,%s,%s)',
                    (mobile, digest, 'b'*64, 'c'*64, 'PASSWORD_RESET', user_id))
                challenge = cursor.fetchone()[0]
                assert challenge
                assert cursor.execute('SELECT km_private.consume_otp(%s,%s,%s)', (mobile, digest, 'c'*64)).fetchone() == (False,)
                assert cursor.execute('SELECT km_private.consume_reset_otp(%s,%s,%s)',
                    (challenge, 'c'*64, 'd'*64)).fetchone() == (user_id,)
                assert cursor.execute('SELECT km_private.consume_reset_otp(%s,%s,%s)',
                    (challenge, 'c'*64, 'e'*64)).fetchone() == (None,)
                cursor.execute('SELECT km_private.create_session(%s,%s,%s)', (user_id, 'f'*64, 600))
                session = cursor.fetchone()[0]
                assert cursor.execute('SELECT km_private.complete_password_reset(%s,%s)',
                    ('d'*64, 'scrypt$16384$8$1$'+'A'*24+'$'+'C'*44)).fetchone() == (True,)
                assert cursor.execute('SELECT km_private.session_active(%s,%s)', (user_id, session)).fetchone() == (False,)
                assert cursor.execute('SELECT km_private.complete_password_reset(%s,%s)',
                    ('d'*64, 'scrypt$16384$8$1$'+'A'*24+'$'+'D'*44)).fetchone() == (False,)
            finally:
                for number in range(5, 0, -1):
                    name = {1:'identity_foundation', 2:'auth_state', 3:'farmer_identity',
                        4:'password_credentials', 5:'otp_recovery'}[number]
                    cursor.execute((migrations / f'{number:04d}_{name}.down.sql').read_text(encoding='utf-8'))
