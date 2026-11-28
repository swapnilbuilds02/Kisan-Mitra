"""Password recovery API checks with an isolated purpose-aware adapter."""

import hashlib
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.identity import AccountState, Actor, Role
from backend.app.main import create_app
from backend.app.passwords import hash_password, verify_password
from backend.tests.key_material import token_service
from backend.tests.test_auth_workflow import FakeIdentity, FakeOtp
from backend.tests.test_password_login import MOBILE, PASSWORD, Credentials, PasswordSessions


class RecoveryOtp(FakeOtp):
    def __init__(self):
        super().__init__()
        self.challenge = uuid4()
        self.purpose = None
        self.used = False
        self.issued_digest = None

    def request_purpose(self, mobile, ip, purpose, subject):
        if subject is None:
            return None
        self.purpose = purpose
        self.subject = subject
        return self.challenge

    def verify_reset(self, challenge, mobile, code, digest):
        if (challenge, mobile, code, self.purpose, self.used) != (self.challenge, MOBILE, '123456', 'PASSWORD_RESET', False):
            return False
        self.used = True
        self.issued_digest = digest
        return True


class RecoveryCredentials(Credentials):
    def __init__(self, identity, otp, sessions):
        super().__init__(identity)
        self.otp = otp
        self.sessions = sessions

    def complete_reset(self, digest, password):
        if digest != self.otp.issued_digest or not self.otp.used or self.otp.issued_digest is None:
            return False
        self.otp.issued_digest = None
        self.encoded = hash_password(password)
        self.sessions.revoke_user(self.identity.actor.id)
        return True

    def change_authenticated(self, subject, current_password, new_password):
        if subject != self.identity.actor.id or not verify_password(current_password, self.encoded):
            return False
        self.encoded = hash_password(new_password)
        self.sessions.revoke_user(subject)
        return True


def setup(role=Role.FARMER, state=AccountState.ACTIVE):
    identity = FakeIdentity(Actor(uuid4(), role, state))
    otp = RecoveryOtp()
    sessions = PasswordSessions()
    creds = RecoveryCredentials(identity, otp, sessions)
    client = TestClient(create_app(identity_store=identity, otp_provider=otp,
        session_store=sessions, credential_store=creds, token_service=token_service()))
    return client, identity, otp, sessions, creds


def test_reset_flow_revokes_session_and_old_password():
    client, identity, otp, sessions, creds = setup()
    login = client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': PASSWORD}).json()
    assert login['access_token']
    assert client.post('/api/v1/auth/password/forgot', json={'mobile_number': MOBILE}).status_code == 202
    response = client.post('/api/v1/auth/password/reset/verify', json={
        'challenge_id': str(otp.challenge), 'mobile_number': MOBILE, 'otp': '123456'})
    assert response.status_code == 200
    reset_token = response.json()['reset_token']
    assert not reset_token.startswith('eyJ')
    assert client.post('/api/v1/auth/password/reset', json={
        'reset_token': reset_token, 'new_password': 'NewSecurePassword123', 'confirm_password': 'NewSecurePassword123'}).status_code == 204
    assert not verify_password(PASSWORD, creds.encoded)
    assert client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': PASSWORD}).status_code == 401
    assert client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': 'NewSecurePassword123'}).status_code == 200
    assert client.get('/api/v1/farmer/overview', headers={'Authorization': 'Bearer '+login['access_token']}).status_code == 401
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': login['refresh_token']}).status_code == 401
    assert client.post('/api/v1/auth/password/reset', json={
        'reset_token': reset_token, 'new_password': 'AnotherPassword123', 'confirm_password': 'AnotherPassword123'}).status_code == 401


def test_unknown_and_restricted_accounts_get_generic_request_response():
    for role, state in [(Role.FARMER, AccountState.SUSPENDED), (Role.SHOP, AccountState.PENDING_APPROVAL), (Role.ADMIN, AccountState.ACTIVE)]:
        client, _, otp, _, _ = setup(role, state)
        assert client.post('/api/v1/auth/password/forgot', json={'mobile_number': MOBILE}).json()['status'] == 'accepted'
        assert otp.purpose is None
    client, _, otp, _, _ = setup()
    assert client.post('/api/v1/auth/password/forgot', json={'mobile_number': '9876543211'}).json()['status'] == 'accepted'


def test_recovery_request_returns_opaque_challenge_for_known_and_unknown_mobile():
    from uuid import UUID
    client, identity, otp, sessions, creds = setup()
    known = client.post('/api/v1/auth/password/forgot',json={'mobile_number':MOBILE})
    unknown = client.post('/api/v1/auth/password/forgot',json={'mobile_number':'9876543211'})
    assert known.status_code == unknown.status_code == 202
    assert known.json()['status'] == unknown.json()['status'] == 'accepted'
    assert UUID(known.json()['challenge_id']) and UUID(unknown.json()['challenge_id'])


def test_purpose_mismatch_and_invalid_reset_requests():
    client, _, otp, _, _ = setup()
    otp.purpose = 'LOGIN'
    request = {'challenge_id': str(otp.challenge), 'mobile_number': MOBILE, 'otp': '123456'}
    assert client.post('/api/v1/auth/password/reset/verify', json=request).status_code == 401
    otp.purpose = 'REGISTRATION'
    assert client.post('/api/v1/auth/password/reset/verify', json=request).status_code == 401
    otp.purpose = 'PASSWORD_RESET'
    assert client.post('/api/v1/auth/password/reset/verify', json={**request, 'mobile_number': '9876543211'}).status_code == 401
    assert client.post('/api/v1/auth/password/reset/verify', json={**request, 'otp': '000000'}).status_code == 401
    assert client.post('/api/v1/auth/password/reset/verify', json=request).status_code == 200
    assert client.post('/api/v1/auth/password/reset/verify', json=request).status_code == 401
    assert client.post('/api/v1/auth/password/reset', json={
        'reset_token': 'x'*50, 'new_password': 'weak', 'confirm_password': 'weak'}).status_code == 400


def test_authenticated_password_change_revokes_existing_token():
    client, _, _, _, _ = setup()
    login = client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': PASSWORD}).json()
    headers = {'Authorization': 'Bearer '+login['access_token']}
    body = {'current_password': PASSWORD, 'new_password': 'ChangedPassword123', 'confirm_password': 'ChangedPassword123'}
    assert client.post('/api/v1/auth/password/change', json={**body, 'current_password': 'WrongPassword123'}, headers=headers).status_code == 401
    assert client.post('/api/v1/auth/password/change', json=body).status_code == 401
    assert client.post('/api/v1/auth/password/change', json=body, headers=headers).status_code == 204
    assert client.get('/api/v1/users/me/profile', headers=headers).status_code == 401
    assert client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': 'ChangedPassword123'}).status_code == 200
