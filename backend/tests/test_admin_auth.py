"""Stage 1E Admin paths with explicitly provisioned, isolated identities."""

from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.identity import AccountState, Actor, Role
from backend.app.main import create_app
from backend.app.passwords import hash_password, verify_password
from backend.tests.key_material import token_service
from backend.tests.test_password_login import MOBILE, PASSWORD, PasswordSessions


class AdminIdentity:
    def __init__(self, role=Role.SUPER_ADMIN, state=AccountState.PENDING_APPROVAL):
        self.actor = Actor(uuid4(), role, state)

    def get_actor(self, subject):
        return self.actor if subject == self.actor.id and self.actor.state != AccountState.PENDING_APPROVAL else None

    def get_actor_by_mobile(self, mobile):
        return self.get_actor(self.actor.id) if mobile == MOBILE else None

    def ready(self):
        return True


class AdminOtp:
    def __init__(self):
        self.challenge = uuid4()
        self.purpose = None
        self.used = False
        self.reset_digest = None
        self.expired = False
        self.admin_requests = 0

    def allow_admin_attempt(self, mobile, ip):
        self.admin_requests += 1
        return self.admin_requests <= 2

    def ready(self):
        return True

    def request_purpose(self, mobile, ip, purpose, subject):
        if subject is None:
            return None
        self.purpose = purpose
        self.subject = subject
        self.challenge = uuid4()
        self.used = False
        return self.challenge

    def verify_admin_onboarding(self, challenge, mobile, code, digest):
        if self.used or self.expired or (challenge, mobile, code, self.purpose) != (self.challenge, MOBILE, '123456', 'ACCOUNT_CLAIM'):
            return False
        self.used = True
        self.onboarding_digest = digest
        return True

    def verify_admin_login(self, challenge, mobile, subject, code):
        if self.used or self.expired or (challenge, mobile, subject, code, self.purpose) != (self.challenge, MOBILE, self.subject, '123456', 'LOGIN'):
            return False
        self.used = True
        return True

    def request_admin_reset(self, mobile, ip, subject):
        return self.request_purpose(mobile, ip, 'PASSWORD_RESET', subject)

    def verify_reset(self, challenge, mobile, code, digest):
        if self.used or self.expired or (challenge, mobile, code, self.purpose) != (self.challenge, MOBILE, '123456', 'PASSWORD_RESET'):
            return False
        self.used = True
        self.reset_digest = digest
        return True


class AdminGate:
    def __init__(self, identity, otp):
        self.identity = identity
        self.otp = otp
        self.provisioned = False
        self.credentials = None

    def candidate(self, mobile):
        if mobile == MOBILE and self.identity.actor.state == AccountState.PENDING_APPROVAL and self.identity.actor.role in (Role.ADMIN, Role.SUPER_ADMIN):
            return self.identity.actor.id
        return None

    def active(self, subject):
        return self.provisioned and subject == self.identity.actor.id and self.identity.actor.state == AccountState.ACTIVE

    def activate(self, digest, password):
        if self.provisioned or digest != getattr(self.otp, 'onboarding_digest', None) or not self.otp.used:
            return False
        self.provisioned = True
        self.identity.actor = Actor(self.identity.actor.id, self.identity.actor.role, AccountState.ACTIVE)
        self.credentials.encoded = hash_password(password)
        return True


class AdminCredentials:
    def __init__(self, identity, gate, otp, sessions):
        self.identity, self.gate, self.otp, self.sessions = identity, gate, otp, sessions
        self.encoded = None
        self.attempts = 0
        self.admin_attempts = 0

    def allow_attempt(self, mobile, ip):
        self.attempts += 1
        return self.attempts <= 5

    def allow_admin_attempt(self, mobile, ip):
        self.admin_attempts += 1
        return self.admin_attempts <= 3

    def find_actor(self, mobile):
        return self.identity.get_actor_by_mobile(mobile)

    def password_hash(self, subject):
        return self.encoded if subject == self.identity.actor.id else None

    def admin_active(self, subject):
        return self.gate.active(subject)

    def complete_reset(self, digest, password):
        if digest != self.otp.reset_digest or not self.gate.active(self.identity.actor.id):
            return False
        self.otp.reset_digest = None
        self.encoded = hash_password(password)
        self.sessions.revoke_user(self.identity.actor.id)
        return True

    def change_authenticated(self, subject, old, new):
        if not self.gate.active(subject) or not verify_password(old, self.encoded):
            return False
        self.encoded = hash_password(new)
        self.sessions.revoke_user(subject)
        return True


class AdminSessions(PasswordSessions):
    def create_admin(self, subject, digest, ttl):
        return self.create(subject, digest, ttl)


def setup(role=Role.SUPER_ADMIN):
    identity, otp, sessions = AdminIdentity(role), AdminOtp(), AdminSessions()
    gate = AdminGate(identity, otp)
    creds = AdminCredentials(identity, gate, otp, sessions)
    gate.credentials = creds
    client = TestClient(create_app(identity_store=identity, otp_provider=otp, session_store=sessions,
                                   credential_store=creds, admin_provisioning=gate, token_service=token_service()))
    return client, identity, otp, sessions, gate, creds


def activate(client, otp):
    requested = client.post('/api/v1/auth/admin/activate/request', json={'mobile_number': MOBILE})
    assert requested.status_code == 202
    verified = client.post('/api/v1/auth/admin/activate/verify', json={
        'challenge_id': requested.json()['challenge_id'], 'mobile_number': MOBILE, 'otp': '123456'})
    assert verified.status_code == 200
    secret = verified.json()['onboarding_token']
    assert client.post('/api/v1/auth/admin/activate/complete', json={
        'onboarding_token': secret, 'password': PASSWORD, 'confirm_password': PASSWORD}).status_code == 204
    return secret


def test_provisioning_requires_verified_bound_otp_and_single_use_authorization():
    client, identity, otp, sessions, gate, creds = setup()
    assert client.post('/api/v1/auth/admin/register', json={}).status_code == 404
    assert client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': PASSWORD}).status_code == 401
    assert client.post('/api/v1/auth/admin/activate/verify', json={
        'challenge_id': str(uuid4()), 'mobile_number': MOBILE, 'otp': '123456'}).status_code == 401
    token = activate(client, otp)
    assert gate.active(identity.actor.id) and verify_password(PASSWORD, creds.encoded)
    assert client.post('/api/v1/auth/admin/activate/complete', json={
        'onboarding_token': token, 'password': PASSWORD, 'confirm_password': PASSWORD}).status_code == 401


def test_admin_password_otp_login_and_privileged_access():
    client, identity, otp, sessions, gate, creds = setup()
    activate(client, otp)
    password = client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': PASSWORD})
    assert password.status_code == 200
    headers = {'Authorization': 'Bearer ' + password.json()['access_token']}
    assert client.get('/api/v1/admin/overview', headers=headers).status_code == 200
    rotated = client.post('/api/v1/auth/refresh', json={'refresh_token': password.json()['refresh_token']})
    assert rotated.status_code == 200
    assert client.get('/api/v1/admin/overview', headers={'Authorization':'Bearer '+rotated.json()['access_token']}).status_code == 200
    assert client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': 'WrongPassword123'}).status_code == 401
    requested = client.post('/api/v1/auth/admin/otp/request', json={'mobile_number': MOBILE})
    verified = client.post('/api/v1/auth/admin/otp/verify', json={
        'challenge_id': requested.json()['challenge_id'], 'mobile_number': MOBILE, 'otp': '123456'})
    assert verified.status_code == 200
    assert client.post('/api/v1/auth/admin/otp/verify', json={
        'challenge_id': requested.json()['challenge_id'], 'mobile_number': MOBILE, 'otp': '123456'}).status_code == 401
    assert client.get('/api/v1/admin/overview', headers={'Authorization': 'Bearer ' + verified.json()['access_token']}).status_code == 200
    assert client.post('/api/v1/auth/logout', headers={'Authorization':'Bearer '+verified.json()['access_token']}).status_code == 204
    assert client.get('/api/v1/admin/overview', headers={'Authorization':'Bearer '+verified.json()['access_token']}).status_code == 401


def test_admin_recovery_revokes_sessions_and_rejects_replay():
    client, identity, otp, sessions, gate, creds = setup()
    activate(client, otp)
    login = client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': PASSWORD}).json()
    assert client.post('/api/v1/auth/password/forgot', json={'mobile_number': MOBILE}).status_code == 202
    verified = client.post('/api/v1/auth/password/reset/verify', json={
        'challenge_id': str(otp.challenge), 'mobile_number': MOBILE, 'otp': '123456'})
    assert verified.status_code == 200
    reset = verified.json()['reset_token']
    assert client.post('/api/v1/auth/password/reset', json={
        'reset_token': reset, 'new_password': 'NewSecurePassword123', 'confirm_password': 'NewSecurePassword123'}).status_code == 204
    assert client.post('/api/v1/auth/password/reset', json={
        'reset_token': reset, 'new_password': 'AnotherPassword123', 'confirm_password': 'AnotherPassword123'}).status_code == 401
    assert client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': PASSWORD}).status_code == 401
    assert client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': 'NewSecurePassword123'}).status_code == 200
    assert client.get('/api/v1/admin/overview', headers={'Authorization': 'Bearer ' + login['access_token']}).status_code == 401
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': login['refresh_token']}).status_code == 401


def test_admin_change_and_revocation_gate():
    client, identity, otp, sessions, gate, creds = setup()
    activate(client, otp)
    login = client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': PASSWORD}).json()
    headers = {'Authorization': 'Bearer ' + login['access_token']}
    assert client.post('/api/v1/auth/password/change', headers=headers, json={
        'current_password': 'wrong', 'new_password': 'NewSecurePassword123',
        'confirm_password': 'NewSecurePassword123'}).status_code == 401
    assert client.post('/api/v1/auth/password/change', headers=headers, json={
        'current_password': PASSWORD, 'new_password': 'NewSecurePassword123',
        'confirm_password': 'NewSecurePassword123'}).status_code == 204
    assert client.get('/api/v1/admin/overview', headers=headers).status_code == 401
    gate.provisioned = False
    assert client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': 'NewSecurePassword123'}).status_code == 401


def test_cross_role_and_unknown_admin_requests_fail_closed():
    client, identity, otp, sessions, gate, creds = setup(Role.FARMER)
    assert client.post('/api/v1/auth/admin/activate/request', json={'mobile_number': MOBILE}).json()['status'] == 'accepted'
    assert client.post('/api/v1/auth/admin/activate/verify', json={
        'challenge_id': str(otp.challenge), 'mobile_number': MOBILE, 'otp': '123456'}).status_code == 401
    assert client.post('/api/v1/auth/admin/otp/request', json={'mobile_number': '9876543211'}).status_code == 202
    assert client.post('/api/v1/auth/password/forgot', json={'mobile_number': '9876543211'}).json()['status'] == 'accepted'


def test_admin_otp_purpose_expiry_and_invalid_code():
    client, identity, otp, sessions, gate, creds = setup()
    activate(client, otp)
    requested = client.post('/api/v1/auth/admin/otp/request', json={'mobile_number': MOBILE}).json()
    body = {'challenge_id': requested['challenge_id'], 'mobile_number': MOBILE, 'otp': '123456'}
    otp.purpose = 'PASSWORD_RESET'
    assert client.post('/api/v1/auth/admin/otp/verify', json=body).status_code == 401
    otp.purpose = 'LOGIN'
    otp.expired = True
    assert client.post('/api/v1/auth/admin/otp/verify', json=body).status_code == 401
    otp.expired = False
    body['otp'] = '000000'
    assert client.post('/api/v1/auth/admin/otp/verify', json=body).status_code == 401


def test_admin_suspension_denies_access_refresh_and_recovery():
    client, identity, otp, sessions, gate, creds = setup()
    activate(client, otp)
    login = client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': PASSWORD}).json()
    identity.actor = Actor(identity.actor.id, Role.SUPER_ADMIN, AccountState.SUSPENDED)
    headers = {'Authorization': 'Bearer ' + login['access_token']}
    assert client.get('/api/v1/admin/overview', headers=headers).status_code == 401
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': login['refresh_token']}).status_code == 401
    assert client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': PASSWORD}).status_code == 401
    assert client.post('/api/v1/auth/password/forgot', json={'mobile_number': MOBILE}).json()['status'] == 'accepted'
    assert otp.purpose != 'PASSWORD_RESET'


def test_admin_password_login_rate_limit_and_unprovisioned_denial():
    client, identity, otp, sessions, gate, creds = setup()
    activate(client, otp)
    for _ in range(6):
        assert client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': 'WrongPassword123'}).status_code == 401
    assert client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': PASSWORD}).status_code == 401
    gate.provisioned = False
    requested = client.post('/api/v1/auth/admin/otp/request', json={'mobile_number': MOBILE})
    assert requested.status_code == 202
    assert client.post('/api/v1/auth/admin/otp/verify', json={
        'challenge_id': requested.json()['challenge_id'], 'mobile_number': MOBILE, 'otp': '123456'}).status_code == 401


def test_admin_otp_requests_have_stricter_hourly_limit():
    client, identity, otp, sessions, gate, creds = setup()
    activate(client, otp)
    first = client.post('/api/v1/auth/admin/otp/request', json={'mobile_number': MOBILE}).json()
    second = client.post('/api/v1/auth/admin/otp/request', json={'mobile_number': MOBILE}).json()
    assert first['status'] == second['status'] == 'accepted'
    assert first['challenge_id'] != second['challenge_id']
    assert otp.admin_requests == 3
    assert client.post('/api/v1/auth/admin/otp/verify', json={
        'challenge_id': second['challenge_id'], 'mobile_number': MOBILE, 'otp': '123456'}).status_code == 401


def test_admin_recent_auth_is_session_bound_and_required_for_partner_decisions():
    client, identity, otp, sessions, gate, creds = setup()
    activate(client, otp)
    login = client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': PASSWORD}).json()
    headers = {'Authorization': 'Bearer ' + login['access_token']}
    target = f'/api/v1/admin/partner-applications/{uuid4()}/approve'
    assert client.post(target, json={'reason':'Reviewed application'}, headers=headers).status_code == 403
    assert client.post('/api/v1/admin/reauth',json={'current_password':'wrong'},headers=headers).status_code == 401
    proof = client.post('/api/v1/admin/reauth',json={'current_password':PASSWORD},headers=headers)
    assert proof.status_code == 200 and proof.json()['expires_in'] == 300
    recent = proof.json()['reauth_token']
    assert client.post(target,json={'reason':'Reviewed application'},headers={**headers,'X-Admin-Reauth':login['access_token']}).status_code == 403
    # Passing recent authentication reaches the decision layer (unconfigured in this fixture).
    assert client.post(target,json={'reason':'Reviewed application'},headers={**headers,'X-Admin-Reauth':recent}).status_code == 409
    second_session = sessions.create(identity.actor.id,'a'*64,600)
    second_headers={'Authorization':'Bearer '+token_service().issue_access(identity.actor.id,second_session),'X-Admin-Reauth':recent}
    assert client.post(target,json={'reason':'Reviewed application'},headers=second_headers).status_code == 403
