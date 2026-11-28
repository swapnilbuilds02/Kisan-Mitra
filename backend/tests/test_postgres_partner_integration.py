"""Guarded PostgreSQL partner application and approval checks."""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

psycopg = pytest.importorskip('psycopg')
from backend.tests.postgres_test_guard import require_disposable_database


def test_partner_application_and_approval_migration():
    dsn=require_disposable_database(psycopg)
    migrations=Path(__file__).resolve().parents[1]/'migrations'
    names={1:'identity_foundation',2:'auth_state',3:'farmer_identity',4:'password_credentials',
        5:'otp_recovery',6:'farmer_onboarding',7:'partner_applications'}
    admin=uuid4()
    with psycopg.connect(dsn,autocommit=True) as connection:
        with connection.cursor() as cursor:
            assert cursor.execute("SELECT to_regclass('public.users')").fetchone()==(None,)
            for number in range(1,8):
                cursor.execute((migrations/f'{number:04d}_{names[number]}.up.sql').read_text(encoding='utf-8'))
            try:
                cursor.execute("INSERT INTO users(id,mobile_number,role,account_state,is_verified) VALUES (%s,'9876543200','admin','active',TRUE)",(admin,))
                cursor.execute("INSERT INTO km_private.consent_documents(document_id,version,approved_for_use) VALUES('dev-partner','dev-1',TRUE)")
                mobile='9876543210'
                challenge=cursor.execute('SELECT km_private.issue_partner_otp(%s,%s,%s,%s,%s)',
                    (mobile,'a'*64,'b'*64,'c'*64,'shop')).fetchone()[0]
                assert challenge
                assert cursor.execute('SELECT km_private.consume_onboarding_otp(%s,%s,%s)',
                    (challenge,'c'*64,'e'*64)).fetchone()==(False,)
                assert cursor.execute('SELECT km_private.consume_partner_registration_otp(%s,%s,%s,%s)',
                    (challenge,'c'*64,'d'*64,'consultant')).fetchone()==(False,)
                assert cursor.execute('SELECT km_private.consume_partner_registration_otp(%s,%s,%s,%s)',
                    (challenge,'c'*64,'d'*64,'shop')).fetchone()==(True,)
                args=('d'*64,'scrypt$16384$8$1$'+'A'*24+'$'+'B'*44,'shop','Shop Name','Owner','','','mr',
                    'Maharashtra','District','Taluka','Town','','','dev-partner','dev-1')
                user_id=cursor.execute('SELECT km_private.complete_partner_application('+','.join(['%s']*16)+')',args).fetchone()[0]
                assert user_id
                assert cursor.execute('SELECT km_private.complete_partner_application('+','.join(['%s']*16)+')',args).fetchone()==(None,)
                application=cursor.execute('SELECT id FROM partner_applications WHERE user_id=%s',(user_id,)).fetchone()[0]
                old_session=cursor.execute('SELECT km_private.create_password_session(%s,%s,%s,%s)',
                    (user_id,'f'*64,600,args[1])).fetchone()[0]
                assert old_session
                def decide(action):
                    with psycopg.connect(dsn,autocommit=True) as other:
                        with other.cursor() as other_cursor:
                            return other_cursor.execute('SELECT km_private.partner_decision(%s,%s,%s,%s)',
                                (application,admin,action,'Reviewed application')).fetchone()[0]
                with ThreadPoolExecutor(max_workers=2) as pool:
                    outcomes=list(pool.map(decide,('approve','reject')))
                assert sorted(outcomes)==[False,True]
                assert cursor.execute('SELECT km_private.session_active(%s,%s)',(user_id,old_session)).fetchone()==(False,)
                assert cursor.execute('SELECT count(*) FROM partner_decisions WHERE application_id=%s',(application,)).fetchone()==(1,)
                cursor.execute('GRANT km_api TO CURRENT_USER')
                cursor.execute('SET ROLE km_api')
                try:
                    with pytest.raises(psycopg.errors.InsufficientPrivilege):
                        cursor.execute('SELECT * FROM partner_applications')
                finally:
                    cursor.execute('RESET ROLE')
                    cursor.execute('REVOKE km_api FROM CURRENT_USER')
            finally:
                cursor.execute('RESET ROLE')
                for number in range(7,0,-1):
                    cursor.execute((migrations/f'{number:04d}_{names[number]}.down.sql').read_text(encoding='utf-8'))
