"""Authentication contract tests; fakes are injected only into TestClient."""

from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from backend.app.auth import AUDIENCE, ISSUER, TokenService
from backend.app.identity import AccountState, Actor, Role
from backend.app.main import create_app
from backend.tests.key_material import key_pair, token_service

TEST_TOKENS = token_service()
MOBILE = "9876543210"


class FakeIdentity:
    def __init__(self, actor):
        self.actor = actor

    def get_actor(self, user_id):
        return self.actor if self.actor.id == user_id else None

    def get_actor_by_mobile(self, mobile):
        return self.actor if mobile == MOBILE else None

    def claim_farmer(self, mobile):
        return self.get_actor_by_mobile(mobile)

    def ready(self):
        return True


def test_legacy_farmer_login_does_not_create_an_identity():
    class UnknownIdentity(FakeIdentity):
        def get_actor_by_mobile(self,mobile):
            return None
        def claim_farmer(self,mobile):
            raise AssertionError('LOGIN must not claim or create an account')
    identity = UnknownIdentity(Actor(uuid4(),Role.FARMER,AccountState.ACTIVE))
    client = TestClient(create_app(identity_store=identity,otp_provider=FakeOtp(),
        session_store=FakeSessions(),token_service=TEST_TOKENS))
    assert client.post('/api/v1/auth/otp/verify',json={'mobile':MOBILE,'code':'123456'}).status_code == 401


class FakeOtp:
    def __init__(self):
        self.requested = []

    def request(self, mobile, client_ip):
        self.requested.append((mobile, client_ip))

    def verify(self, mobile, code):
        return mobile == MOBILE and code == "123456"

    def ready(self):
        return True


class ProvisionedAdmins:
    """Explicit test-only record of provisioned Admin identities."""
    def active(self, subject):
        return True


class FakeSessions:
    def __init__(self):
        self.lock = Lock()
        self.records = {}
        self.consumed = {}

    def create(self, user_id, refresh_hash, ttl_seconds):
        session_id = uuid4()
        self.records[session_id] = (user_id, refresh_hash)
        self.consumed[session_id] = set()
        return session_id

    def active(self, user_id, session_id):
        return session_id in self.records and self.records[session_id][0] == user_id

    def rotate(self, session_id, old_hash, new_hash, ttl_seconds):
        with self.lock:
            record = self.records.get(session_id)
            if record is None:
                return "invalid", None
            user_id, current_hash = record
            if old_hash in self.consumed[session_id]:
                self.revoke_user(user_id)
                return "reused", user_id
            if old_hash != current_hash:
                return "invalid", None
            self.consumed[session_id].add(old_hash)
            self.records[session_id] = (user_id, new_hash)
            return "rotated", user_id

    def revoke(self, session_id):
        self.records.pop(session_id, None)

    def revoke_user(self, user_id):
        for session_id, record in list(self.records.items()):
            if record[0] == user_id:
                self.revoke(session_id)

    def ready(self):
        return True


@pytest.fixture
def setup_auth():
    actor = Actor(uuid4(), Role.FARMER, AccountState.ACTIVE)
    identity, otp, sessions = FakeIdentity(actor), FakeOtp(), FakeSessions()
    client = TestClient(create_app(identity_store=identity, otp_provider=otp, session_store=sessions,
                                   token_service=TEST_TOKENS, admin_provisioning=ProvisionedAdmins()))
    return client, identity, otp, sessions


def test_otp_issuance_requires_correct_code_and_existing_active_user(setup_auth):
    client, identity, otp, sessions = setup_auth
    assert client.post("/api/v1/auth/otp/request", json={"mobile": MOBILE}).status_code == 202
    assert otp.requested == [(MOBILE, "testclient")]
    assert client.post("/api/v1/auth/otp/verify", json={"mobile": MOBILE, "code": "000000"}).status_code == 401
    assert sessions.records == {}
    response = client.post("/api/v1/auth/otp/verify", json={"mobile": MOBILE, "code": "123456"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    pair = response.json()
    assert pair["expires_in"] == 900
    token = pair["access_token"]
    assert client.get("/api/v1/users/me/profile", headers={"Authorization": f"Bearer {token}"}).json()["role"] == "farmer"
    assert "role" not in TEST_TOKENS.decode_access(token).__dict__

    identity.actor = Actor(identity.actor.id, Role.FARMER, AccountState.SUSPENDED)
    assert client.get("/api/v1/users/me/profile", headers={"Authorization": f"Bearer {token}"}).status_code == 403


def test_otp_cannot_issue_partner_or_admin_session(setup_auth):
    client, identity, _, sessions = setup_auth
    for role in (Role.SHOP, Role.CONSULTANT, Role.ADMIN, Role.SUPER_ADMIN):
        identity.actor = Actor(identity.actor.id, role, AccountState.ACTIVE)
        result = client.post("/api/v1/auth/otp/verify", json={"mobile": MOBILE, "code": "123456"})
        assert (result.status_code, result.json()["detail"]) == (401, "INVALID_OTP")
    assert sessions.records == {}


def test_refresh_rotation_reuse_revokes_all_sessions(setup_auth):
    client, identity, otp, sessions = setup_auth
    first = client.post("/api/v1/auth/otp/verify", json={"mobile": MOBILE, "code": "123456"}).json()
    second = client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert second.status_code == 200
    assert second.headers["cache-control"] == "no-store"
    second_pair = second.json()
    assert second_pair["refresh_token"] != first["refresh_token"]
    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert (reuse.status_code, reuse.json()["detail"]) == (401, "INVALID_REFRESH_TOKEN")
    assert sessions.records == {}
    assert client.get("/api/v1/farmer/overview", headers={"Authorization": f"Bearer {second_pair['access_token']}"}).status_code == 401


def test_concurrent_refresh_has_one_success_and_replay_revokes_session(setup_auth):
    client, _, _, sessions = setup_auth
    first = client.post("/api/v1/auth/otp/verify", json={"mobile": MOBILE, "code": "123456"}).json()
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(client.post, "/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}) for _ in range(2)]
        results = [future.result() for future in futures]
    assert sorted(response.status_code for response in results) == [200, 401]
    assert sessions.records == {}


def test_unknown_account_has_same_public_otp_error(setup_auth):
    client, identity, _, sessions = setup_auth
    identity.actor = None
    response = client.post("/api/v1/auth/otp/verify", json={"mobile": MOBILE, "code": "123456"})
    assert (response.status_code, response.json()["detail"]) == (401, "INVALID_OTP")
    assert sessions.records == {}


def test_logout_revokes_access_and_refresh(setup_auth):
    client, _, _, sessions = setup_auth
    pair = client.post("/api/v1/auth/otp/verify", json={"mobile": MOBILE, "code": "123456"}).json()
    headers = {"Authorization": f"Bearer {pair['access_token']}"}
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/users/me/profile", headers=headers).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": pair["refresh_token"]}).status_code == 401


def test_role_cannot_be_escalated_by_token_or_session(setup_auth):
    client, identity, _, _ = setup_auth
    pair = client.post("/api/v1/auth/otp/verify", json={"mobile": MOBILE, "code": "123456"}).json()
    headers = {"Authorization": f"Bearer {pair['access_token']}"}
    assert client.get("/api/v1/admin/overview", headers=headers).status_code == 403
    identity.actor = Actor(identity.actor.id, Role.ADMIN, AccountState.ACTIVE)
    assert client.get("/api/v1/admin/overview", headers=headers).status_code == 200
    assert client.get("/api/v1/farmer/overview", headers=headers).status_code == 403


def test_default_auth_endpoints_fail_closed():
    client = TestClient(create_app(token_service=TEST_TOKENS))
    assert client.post("/api/v1/auth/otp/request", json={"mobile": MOBILE}).status_code == 503
    assert client.post("/api/v1/auth/otp/verify", json={"mobile": MOBILE, "code": "123456"}).status_code == 503
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": "x" * 60}).status_code == 401
    valid_shape = f"{uuid4()}." + "x" * 43
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": valid_shape}).status_code == 503
    malformed = f"{uuid4()}." + "é" * 43
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": malformed}).status_code == 401


def test_token_rejects_wrong_type_and_invalid_secret(setup_auth):
    with pytest.raises(ValueError):
        TokenService("invalid", {}, "missing")
    client, _, _, _ = setup_auth
    pair = client.post("/api/v1/auth/otp/verify", json={"mobile": MOBILE, "code": "123456"}).json()
    claims = jwt.decode(pair["access_token"], key_pair("test-v1")[1], algorithms=["RS256"], audience=AUDIENCE, issuer=ISSUER)
    claims["typ"] = "refresh"
    wrong_type = jwt.encode(claims, key_pair("test-v1")[0], algorithm="RS256", headers={"kid": "test-v1"})
    assert client.get("/api/v1/users/me/profile", headers={"Authorization": f"Bearer {wrong_type}"}).status_code == 401


def test_cross_user_identity_is_never_returned(setup_auth):
    client, identity, _, sessions = setup_auth
    pair = client.post("/api/v1/auth/otp/verify", json={"mobile": MOBILE, "code": "123456"}).json()
    claims = jwt.decode(pair["access_token"], key_pair("test-v1")[1], algorithms=["RS256"], audience=AUDIENCE, issuer=ISSUER)
    claims["sub"] = str(uuid4())
    forged = jwt.encode(claims, key_pair("test-v1")[0], algorithm="RS256", headers={"kid": "test-v1"})
    assert client.get("/api/v1/users/me/profile", headers={"Authorization": f"Bearer {forged}"}).status_code == 401
