"""Shared password login security and regression checks."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.identity import AccountState, Actor, Role
from backend.app.main import create_app
from backend.app.passwords import hash_password, verify_password
from backend.tests.key_material import token_service
from backend.tests.test_auth_workflow import FakeIdentity, FakeOtp, FakeSessions

MOBILE = '9876543210'
PASSWORD = 'CorrectHorse1234'


class Credentials:
    def __init__(self, identity):
        self.identity = identity
        self.encoded = hash_password(PASSWORD)
        self.attempts = 0

    def allow_attempt(self, mobile, ip):
        self.attempts += 1
        return self.attempts <= 5

    def find_actor(self, mobile):
        return self.identity.get_actor_by_mobile(mobile)

    def password_hash(self, subject):
        return self.encoded


class PasswordSessions(FakeSessions):
    def create_password(self, user_id, refresh_hash, ttl_seconds, credential_hash):
        return self.create(user_id, refresh_hash, ttl_seconds)


def client_for(role=Role.FARMER, state=AccountState.ACTIVE):
    identity = FakeIdentity(Actor(uuid4(), role, state))
    creds = Credentials(identity)
    sessions = PasswordSessions()
    tokens = token_service()
    client = TestClient(create_app(identity_store=identity, credential_store=creds,
        otp_provider=FakeOtp(), session_store=sessions, token_service=tokens))
    return client, identity, creds, sessions, tokens


def test_password_hash_and_malformed_hash():
    encoded = hash_password(PASSWORD)
    assert PASSWORD not in encoded
    assert verify_password(PASSWORD, encoded)
    assert not verify_password('WrongHorse1234', encoded)
    assert not verify_password(PASSWORD, 'scrypt$999999999$8$1$bad$bad')
    assert not verify_password(PASSWORD, None)
    with pytest.raises(ValueError):
        hash_password('short')


def test_password_login_uses_existing_rs256_session_and_mobile_normalization():
    client, identity, _, sessions, tokens = client_for()
    result = client.post('/api/v1/auth/password/login', json={'mobile_number': '+91'+MOBILE, 'password': PASSWORD})
    assert result.status_code == 200
    assert result.headers['cache-control'] == 'no-store'
    access = result.json()['access_token']
    decoded = tokens.decode_access(access)
    assert decoded.user_id == identity.actor.id and sessions.active(decoded.user_id, decoded.session_id)
    assert client.get('/api/v1/farmer/overview', headers={'Authorization': 'Bearer '+access}).status_code == 200


@pytest.mark.parametrize('role,state', [(Role.FARMER, AccountState.SUSPENDED),
    (Role.SHOP, AccountState.PENDING_APPROVAL), (Role.CONSULTANT, AccountState.ACTIVE),
    (Role.ADMIN, AccountState.ACTIVE), (Role.SUPER_ADMIN, AccountState.ACTIVE)])
def test_password_login_denies_unapproved_roles_and_states(role, state):
    client, _, _, sessions, _ = client_for(role, state)
    result = client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': PASSWORD})
    assert result.status_code == 401 and result.json()['detail'] == 'INVALID_CREDENTIALS'
    assert not sessions.records


def test_invalid_unknown_and_rate_limited_login_are_generic():
    client, identity, creds, sessions, _ = client_for()
    for mobile, password in [(MOBILE, 'WrongHorse1234'), ('9876543211', PASSWORD)]:
        response = client.post('/api/v1/auth/password/login', json={'mobile_number': mobile, 'password': password})
        assert response.status_code == 401 and response.json()['detail'] == 'INVALID_CREDENTIALS'
    for _ in range(4):
        client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': 'WrongHorse1234'})
    assert creds.attempts == 6 and not sessions.records
    assert client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': PASSWORD}).status_code == 401


def test_otp_farmer_regression():
    client, _, _, _, _ = client_for()
    assert client.post('/api/v1/auth/otp/verify', json={'mobile': MOBILE, 'code': '123456'}).status_code == 200
