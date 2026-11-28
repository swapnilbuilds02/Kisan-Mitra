"""Guarded test for atomic Farmer onboarding and restricted table access."""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

psycopg = pytest.importorskip('psycopg')
from backend.tests.postgres_test_guard import require_disposable_database
from backend.app.farmer_onboarding import PostgresFarmerOnboarding
from backend.app.identity import PostgresIdentityStore


def test_onboarding_migration_and_atomic_claim():
    dsn = require_disposable_database(psycopg)
    migrations = Path(__file__).resolve().parents[1] / 'migrations'
    names = {1:'identity_foundation',2:'auth_state',3:'farmer_identity',4:'password_credentials',
        5:'otp_recovery',6:'farmer_onboarding'}
    with psycopg.connect(dsn, autocommit=True) as connection:
        with connection.cursor() as cursor:
            assert cursor.execute("SELECT to_regclass('public.users')").fetchone() == (None,)
            for number in range(1,7):
                cursor.execute((migrations / f'{number:04d}_{names[number]}.up.sql').read_text(encoding='utf-8'))
            try:
                cursor.execute("INSERT INTO km_private.consent_documents(document_id,version,approved_for_use) VALUES('dev-service','dev-1',TRUE)")
                mobile = '9876543210'
                assert cursor.execute('SELECT * FROM km_private.farmer_onboarding_target(%s)', (mobile,)).fetchone() == (None,'REGISTRATION')
                challenge = cursor.execute('SELECT km_private.issue_purpose_otp(%s,%s,%s,%s,%s,%s)',
                    (mobile,'a'*64,'b'*64,'c'*64,'REGISTRATION',None)).fetchone()[0]
                assert challenge
                assert cursor.execute('SELECT km_private.consume_onboarding_otp(%s,%s,%s)',
                    (challenge,'c'*64,'d'*64)).fetchone() == (True,)
                profile = dict(full_name='Farmer Test',preferred_language='mr',village='Village',
                    taluka='Taluka',district='District',state='Maharashtra',pincode='411001',
                    consent_document_id='dev-service',consent_version='dev-1')
                adapter = PostgresFarmerOnboarding(PostgresIdentityStore(dsn))
                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(lambda _: adapter.complete('d'*64, 'StrongPassword123', profile), range(2)))
                assert sum(result is not None for result in results) == 1
                farmer_id = next(result for result in results if result is not None)
                assert adapter.complete('d'*64, 'OtherPassword123', profile) is None
                assert cursor.execute('SELECT count(*) FROM users WHERE mobile_number=%s', (mobile,)).fetchone() == (1,)
                assert cursor.execute('SELECT count(*) FROM farmer_profiles WHERE user_id=%s', (farmer_id,)).fetchone() == (1,)
                assert cursor.execute('SELECT count(*) FROM farmer_consents WHERE user_id=%s', (farmer_id,)).fetchone() == (1,)
                cursor.execute('GRANT km_api TO CURRENT_USER')
                cursor.execute('SET ROLE km_api')
                try:
                    with pytest.raises(psycopg.errors.InsufficientPrivilege):
                        cursor.execute('SELECT * FROM farmer_profiles')
                finally:
                    cursor.execute('RESET ROLE')
                    cursor.execute('REVOKE km_api FROM CURRENT_USER')
            finally:
                cursor.execute('RESET ROLE')
                for number in range(6,0,-1):
                    cursor.execute((migrations / f'{number:04d}_{names[number]}.down.sql').read_text(encoding='utf-8'))
