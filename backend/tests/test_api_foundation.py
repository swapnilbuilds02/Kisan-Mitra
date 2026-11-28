"""Phase 1 API authorization checks with a disposable identity store."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from backend.app.identity import AccountState, Actor, Role
from backend.app.main import AUDIENCE, ISSUER, create_app
from backend.tests.key_material import key_pair, token_service
from backend.tests.test_auth_workflow import ProvisionedAdmins

TEST_TOKENS = token_service()
SESSION_ID = uuid4()


class FakeStore:
    def __init__(self, actor=None, available=True):
        self.actor = actor
        self.available = available

    def get_actor(self, user_id):
        if not self.available:
            raise ConnectionError("database unavailable")
        return self.actor if self.actor and self.actor.id == user_id else None

    def get_actor_by_mobile(self, mobile):
        return self.actor

    def claim_farmer(self, mobile):
        return self.actor

    def prepare_farmer(self, mobile, operator_id, reason):
        return uuid4()

    def ready(self):
        return self.available


class FakeSessions:
    def __init__(self, active=True):
        self.is_active = active

    def active(self, user_id, session_id):
        return self.is_active and session_id == SESSION_ID

    def ready(self):
        return self.is_active


def token(user_id, **overrides):
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id), "sid": str(SESSION_ID), "jti": str(uuid4()),
        "typ": "access", "iat": now, "nbf": now,
        "exp": now + timedelta(minutes=10), "iss": ISSUER, "aud": AUDIENCE,
    }
    claims.update(overrides)
    return jwt.encode(claims, key_pair("test-v1")[0], algorithm="RS256", headers={"kid": "test-v1"})


def call(client, path, bearer=None):
    headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}
    return client.get(path, headers=headers)


def test_health_and_unconfigured_service_fail_closed():
    client = TestClient(create_app())
    assert call(client, "/health/live").json() == {"status": "alive"}
    assert call(client, "/health/ready").status_code == 503
    assert call(client, "/api/v1/farmer/overview").status_code == 401
    assert call(client, "/api/v1/farmer/overview", token(uuid4())).status_code == 503


def test_token_validation_and_unknown_identity():
    user_id = uuid4()
    client = TestClient(create_app(identity_store=FakeStore(), token_service=TEST_TOKENS, session_store=FakeSessions()))
    path = "/api/v1/users/me/profile"
    assert call(client, path).status_code == 401
    assert call(client, path, "garbage").status_code == 401
    assert call(client, path, token(user_id) + "tampered").status_code == 401
    assert call(client, path, token(user_id, exp=datetime.now(timezone.utc) - timedelta(seconds=1))).status_code == 401
    assert call(client, path, token(user_id, aud="wrong-client")).status_code == 401
    unsigned = jwt.encode({"sub": str(user_id), "sid": str(SESSION_ID)}, key="", algorithm="none")
    assert call(client, path, unsigned).status_code == 401
    assert call(client, path, token(user_id)).json()["detail"] == "UNKNOWN_USER"


@pytest.mark.parametrize("role,path", [
    (Role.FARMER, "/api/v1/farmer/overview"),
    (Role.SHOP, "/api/v1/partner/overview"),
    (Role.CONSULTANT, "/api/v1/partner/overview"),
    (Role.ADMIN, "/api/v1/admin/overview"),
    (Role.SUPER_ADMIN, "/api/v1/admin/overview"),
])
def test_each_role_can_enter_only_its_shell(role, path):
    actor = Actor(uuid4(), role, AccountState.ACTIVE)
    client = TestClient(create_app(identity_store=FakeStore(actor), token_service=TEST_TOKENS, session_store=FakeSessions(), admin_provisioning=ProvisionedAdmins()))
    credential = token(actor.id, role="super_admin")  # untrusted token claim
    assert call(client, path, credential).status_code == 200
    profile = call(client, "/api/v1/users/me/profile", credential)
    assert profile.json()["role"] == role.value
    for other in ("/api/v1/farmer/overview", "/api/v1/partner/overview", "/api/v1/admin/overview"):
        if other != path:
            assert call(client, other, credential).status_code == 403


@pytest.mark.parametrize("state,detail", [
    (AccountState.PENDING_APPROVAL, "PENDING_APPROVAL"),
    (AccountState.SUSPENDED, "ACCOUNT_SUSPENDED"),
    (AccountState.EXPIRED, "SUBSCRIPTION_EXPIRED"),
])
def test_inactive_partner_cannot_read_profile_or_shell(state, detail):
    actor = Actor(uuid4(), Role.SHOP, state)
    client = TestClient(create_app(identity_store=FakeStore(actor), token_service=TEST_TOKENS, session_store=FakeSessions()))
    for path in ("/api/v1/users/me/profile", "/api/v1/partner/overview"):
        result = call(client, path, token(actor.id))
        assert (result.status_code, result.json()["detail"]) == (403, detail)


def test_database_outage_denies_access_and_readiness():
    actor = Actor(uuid4(), Role.FARMER, AccountState.ACTIVE)
    client = TestClient(create_app(identity_store=FakeStore(actor, False), token_service=TEST_TOKENS, session_store=FakeSessions()))
    assert call(client, "/health/ready").status_code == 503
    result = call(client, "/api/v1/farmer/overview", token(actor.id))
    assert (result.status_code, result.json()["detail"]) == (503, "AUTH_BACKEND_UNAVAILABLE")


def test_admin_farmer_preparation_requires_role_and_normalizes_mobile():
    admin = Actor(uuid4(), Role.ADMIN, AccountState.ACTIVE)
    store = FakeStore(admin)
    received = []
    store.prepare_farmer = lambda mobile, operator_id, reason: received.append((mobile, operator_id, reason)) or uuid4()
    client = TestClient(create_app(identity_store=store, token_service=TEST_TOKENS, session_store=FakeSessions(), admin_provisioning=ProvisionedAdmins()))
    result = client.post(
        "/api/v1/admin/farmers/pre-register",
        headers={"Authorization": f"Bearer {token(admin.id)}"},
        json={"mobile": "+919876543210", "reason": "Owner requested registration"},
    )
    assert result.status_code == 201
    assert received == [("9876543210", admin.id, "Owner requested registration")]
    store.actor = Actor(admin.id, Role.FARMER, AccountState.ACTIVE)
    denied = client.post(
        "/api/v1/admin/farmers/pre-register",
        headers={"Authorization": f"Bearer {token(admin.id)}"},
        json={"mobile": "9876543210", "reason": "Owner requested registration"},
    )
    assert denied.status_code == 403
    assert len(received) == 1


def test_invalid_mobile_rejected_before_otp_or_preparation():
    client = TestClient(create_app(token_service=TEST_TOKENS))
    for mobile in ("123", "1111111111", "+19876543210", "98765-43210"):
        assert client.post("/api/v1/auth/otp/request", json={"mobile": mobile}).status_code == 422
