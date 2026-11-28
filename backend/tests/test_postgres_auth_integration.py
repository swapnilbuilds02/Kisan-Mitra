"""Auth state integration on a fresh, isolated localhost km_test_* database."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")
from backend.tests.postgres_test_guard import require_disposable_database

from backend.app.postgres_auth import PostgresOtpProvider, PostgresSessionStore


class RecordingSender:
    def __init__(self):
        self.sent = []

    def send(self, mobile, code):
        self.sent.append((mobile, code))

    def ready(self):
        return True


def test_persistent_sessions_and_otp_limits():
    dsn = require_disposable_database(psycopg)

    migration_dir = Path(__file__).resolve().parents[1] / "migrations"
    user_id = uuid4()
    with psycopg.connect(dsn, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.users')")
            assert cursor.fetchone() == (None,), "Identity schema already exists"
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname='km_api'")
            assert cursor.fetchone() is None, "km_api role already exists on this server"
            cursor.execute((migration_dir / "0001_identity_foundation.up.sql").read_text(encoding="utf-8"))
            try:
                cursor.execute((migration_dir / "0002_auth_state.up.sql").read_text(encoding="utf-8"))
                try:
                    cursor.execute("INSERT INTO users(id,mobile_number,role,account_state,is_verified) VALUES (%s,'9876543210','farmer','active',TRUE)", (user_id,))

                    sender = RecordingSender()
                    otp = PostgresOtpProvider(dsn, "local-test-pepper-32-bytes-minimum-value", sender)
                    sessions = PostgresSessionStore(dsn)
                    otp.request("9876543210", "127.0.0.1")
                    assert len(sender.sent) == 1
                    code = sender.sent[0][1]
                    otp.request("9876543210", "127.0.0.1")  # cooldown
                    assert len(sender.sent) == 1
                    assert not otp.verify("9876543210", "000000" if code != "000000" else "999999")
                    assert otp.verify("9876543210", code)
                    assert not otp.verify("9876543210", code)  # single use

                    for _ in range(2):
                        cursor.execute("UPDATE auth_otp_challenges SET next_request_at = now() - interval '1 second' WHERE mobile_number='9876543210'")
                        otp.request("9876543210", "127.0.0.1")
                    assert len(sender.sent) == 3
                    cursor.execute("UPDATE auth_otp_challenges SET next_request_at = now() - interval '1 second' WHERE mobile_number='9876543210'")
                    otp.request("9876543210", "127.0.0.1")
                    otp.request("9876543211", "127.0.0.1")  # IP hourly limit
                    assert len(sender.sent) == 3

                    otp.request("9876543212", "127.0.0.2")
                    assert len(sender.sent) == 4
                    for _ in range(5):
                        assert not otp.verify("9876543212", "000000" if sender.sent[-1][1] != "000000" else "999999")
                    assert not otp.verify("9876543212", sender.sent[-1][1])  # max attempts
                    otp.request("9876543213", "127.0.0.3")
                    cursor.execute("UPDATE auth_otp_challenges SET expires_at = now() - interval '1 second' WHERE mobile_number='9876543213'")
                    assert not otp.verify("9876543213", sender.sent[-1][1])

                    old = hashlib.sha256(b"first-refresh-secret").hexdigest()
                    new_a = hashlib.sha256(b"second-refresh-secret").hexdigest()
                    new_b = hashlib.sha256(b"third-refresh-secret").hexdigest()
                    session_id = sessions.create(user_id, old, 60)
                    assert PostgresSessionStore(dsn).active(user_id, session_id)
                    with ThreadPoolExecutor(max_workers=2) as executor:
                        futures = [executor.submit(sessions.rotate, session_id, old, digest, 60) for digest in (new_a, new_b)]
                        results = [future.result() for future in futures]
                    assert {result for result, _ in results} == {"rotated", "reused"}
                    assert not PostgresSessionStore(dsn).active(user_id, session_id)
                    session_two = sessions.create(user_id, old, 60)
                    sessions.revoke(session_two)
                    assert not PostgresSessionStore(dsn).active(user_id, session_two)

                    cursor.execute("UPDATE auth_sessions SET expires_at = now() - interval '1 second' WHERE id = %s", (session_id,))
                    assert not sessions.active(user_id, session_id)
                    cursor.execute("SELECT count(*) FROM auth_security_events WHERE action IN ('OTP_ISSUED','OTP_VERIFIED','REFRESH_REUSED','SESSION_REVOKED')")
                    assert cursor.fetchone()[0] >= 4
                    cursor.execute("SELECT count(*) FROM information_schema.columns WHERE table_name='auth_security_events' AND column_name IN ('code','refresh_token','code_hash','refresh_hash')")
                    assert cursor.fetchone() == (0,)

                    # Restricted role has no raw access even though its narrow
                    # functions are executable.
                    cursor.execute("GRANT km_api TO CURRENT_USER")
                    cursor.execute("GRANT SELECT ON auth_sessions TO km_api")
                    cursor.execute("SET ROLE km_api")
                    try:
                        cursor.execute("SELECT count(*) FROM auth_sessions")
                        assert cursor.fetchone() == (0,)  # RLS deny with temporary SELECT
                        with pytest.raises(psycopg.errors.InsufficientPrivilege):
                            cursor.execute("UPDATE auth_sessions SET revoked_at=now() WHERE id=%s", (session_two,))
                        cursor.execute("SELECT km_private.session_active(%s,%s)", (user_id, session_two))
                        assert cursor.fetchone() == (False,)
                    finally:
                        cursor.execute("RESET ROLE")
                        cursor.execute("REVOKE SELECT ON auth_sessions FROM km_api")
                        cursor.execute("REVOKE km_api FROM CURRENT_USER")
                finally:
                    cursor.execute("RESET ROLE")
                    cursor.execute("REVOKE SELECT ON auth_sessions FROM km_api")
                    cursor.execute("REVOKE km_api FROM CURRENT_USER")
                    cursor.execute((migration_dir / "0002_auth_state.down.sql").read_text(encoding="utf-8"))
            finally:
                cursor.execute((migration_dir / "0001_identity_foundation.down.sql").read_text(encoding="utf-8"))
            cursor.execute("SELECT to_regclass('public.auth_sessions'), to_regclass('public.users')")
            assert cursor.fetchone() == (None, None)
