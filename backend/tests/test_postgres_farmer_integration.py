"""Farmer claim and pre-registration checks on an isolated localhost database."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")
from backend.tests.postgres_test_guard import require_disposable_database

from backend.app.identity import PostgresIdentityStore
from backend.app.auth import AuthWorkflow, AuthenticationError
from backend.app.postgres_auth import PostgresOtpProvider, PostgresSessionStore
from backend.tests.key_material import token_service


class RecordingSender:
    def __init__(self):
        self.sent = []

    def send(self, mobile, code):
        self.sent.append((mobile, code))

    def ready(self):
        return True


def test_farmer_claim_is_atomic_and_audited():
    dsn = require_disposable_database(psycopg)
    migrations = Path(__file__).resolve().parents[1] / "migrations"
    admin_id = uuid4()
    with psycopg.connect(dsn, autocommit=True) as connection:
        with connection.cursor() as cursor:
            assert cursor.execute("SELECT to_regclass('public.users')").fetchone() == (None,)
            assert cursor.execute("SELECT 1 FROM pg_roles WHERE rolname='km_api'").fetchone() is None
            cursor.execute((migrations / "0001_identity_foundation.up.sql").read_text(encoding="utf-8"))
            try:
                cursor.execute((migrations / "0002_auth_state.up.sql").read_text(encoding="utf-8"))
                try:
                    cursor.execute((migrations / "0003_farmer_identity.up.sql").read_text(encoding="utf-8"))
                    try:
                        cursor.execute("INSERT INTO users(id,mobile_number,role,account_state,is_verified) VALUES (%s,'9876543200','admin','active',TRUE)", (admin_id,))
                        identities = PostgresIdentityStore(dsn)
                        prepared = identities.prepare_farmer("9876543210", admin_id, "Owner registration request")
                        assert identities.prepare_farmer("9876543210", admin_id, "Owner registration request") == prepared
                        cursor.execute("SELECT is_verified, account_state FROM users WHERE id=%s", (prepared,))
                        assert cursor.fetchone() == (False, "pending_approval")

                        sender = RecordingSender()
                        otp = PostgresOtpProvider(dsn, "local-test-pepper-32-bytes-minimum-value", sender)
                        workflow = AuthWorkflow(identities, otp, PostgresSessionStore(dsn), token_service())
                        workflow.request_otp("9876543210", "127.0.0.1")
                        assert len(sender.sent) == 1
                        with ThreadPoolExecutor(max_workers=2) as executor:
                            futures = [executor.submit(workflow.verify_otp, "9876543210", sender.sent[0][1]) for _ in range(2)]
                            outcomes = []
                            for future in futures:
                                try:
                                    outcomes.append(future.result())
                                except AuthenticationError:
                                    outcomes.append(None)
                        assert sum(outcome is not None for outcome in outcomes) == 1
                        issued = next(outcome for outcome in outcomes if outcome is not None)
                        assert issued["access_token"]
                        cursor.execute("SELECT count(*) FROM users WHERE mobile_number='9876543210'")
                        assert cursor.fetchone() == (1,)
                        cursor.execute("SELECT is_verified, account_state FROM users WHERE id=%s", (prepared,))
                        assert cursor.fetchone() == (True, "active")

                        with ThreadPoolExecutor(max_workers=2) as executor:
                            futures = [executor.submit(identities.claim_farmer, "9876543211") for _ in range(2)]
                            new_claims = [future.result() for future in futures]
                        assert len({actor.id for actor in new_claims}) == 1
                        assert identities.claim_farmer("9876543200") is None  # admin mobile cannot be claimed
                        with pytest.raises(Exception):
                            identities.prepare_farmer("9876543212", prepared, "Unauthorized request")
                        cursor.execute("SELECT action, count(*) FROM audit_logs WHERE action IN ('FARMER_PREPARED','FARMER_ACCOUNT_CLAIMED','FARMER_SELF_REGISTERED') GROUP BY action")
                        assert dict(cursor.fetchall()) == {
                            "FARMER_PREPARED": 1, "FARMER_ACCOUNT_CLAIMED": 1, "FARMER_SELF_REGISTERED": 1,
                        }
                        assert cursor.execute("SELECT count(*) FROM audit_logs WHERE action='FARMER_PREPARE_EXISTING'").fetchone() == (1,)

                        cursor.execute("GRANT km_api TO CURRENT_USER")
                        cursor.execute("GRANT SELECT ON users TO km_api")
                        cursor.execute("SET ROLE km_api")
                        try:
                            assert cursor.execute("SELECT count(*) FROM users").fetchone() == (0,)
                            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                                cursor.execute("UPDATE users SET is_verified=FALSE WHERE id=%s", (prepared,))
                        finally:
                            cursor.execute("RESET ROLE")
                            cursor.execute("REVOKE SELECT ON users FROM km_api")
                            cursor.execute("REVOKE km_api FROM CURRENT_USER")
                    finally:
                        cursor.execute("RESET ROLE")
                        cursor.execute("REVOKE SELECT ON users FROM km_api")
                        cursor.execute("REVOKE km_api FROM CURRENT_USER")
                        cursor.execute((migrations / "0003_farmer_identity.down.sql").read_text(encoding="utf-8"))
                finally:
                    cursor.execute((migrations / "0002_auth_state.down.sql").read_text(encoding="utf-8"))
            finally:
                cursor.execute((migrations / "0001_identity_foundation.down.sql").read_text(encoding="utf-8"))
