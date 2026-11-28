"""Farmer registration route contract with isolated identity and delivery adapters."""

from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.identity import AccountState, Actor, Role
from backend.app.main import create_app
from backend.tests.key_material import token_service
from backend.tests.test_password_login import PasswordSessions, MOBILE
from backend.tests.test_auth_workflow import FakeIdentity
from backend.app.passwords import hash_password


PROFILE = dict(full_name='Farmer One', preferred_language='mr', village='Village',
    taluka='Taluka', district='District', state='Maharashtra', pincode='411001')


class OnboardingOtp:
    def __init__(self):
        self.challenge = uuid4()
        self.purpose = None
        self.used = False

    def ready(self): return True
    def request(self, mobile, ip): pass
    def verify(self, mobile, code): return mobile == MOBILE and code == '123456'

    def request_purpose(self, mobile, ip, purpose, subject):
        self.purpose = purpose
        return self.challenge

    def verify_onboarding(self, challenge, mobile, code, digest):
        if self.used or challenge != self.challenge or mobile != MOBILE or code != '123456': return False
        self.used = True
        self.digest = digest
        return True


class OnboardingStore:
    def __init__(self, identity, otp, pending=False):
        self.identity, self.otp, self.pending = identity, otp, pending
        self.used = False
        self.saved = None
        self.credentials = None

    def target(self, mobile):
        if mobile != MOBILE: return None
        return (self.identity.actor.id if self.pending else None,
                'ACCOUNT_CLAIM' if self.pending else 'REGISTRATION')

    def complete(self, digest, password, profile):
        if self.used or not self.otp.used or digest != self.otp.digest: return None
        self.used = True
        self.saved = profile
        if self.credentials is not None:
            self.credentials.encoded = hash_password(password)
        self.identity.actor = Actor(self.identity.actor.id, Role.FARMER, AccountState.ACTIVE)
        return self.identity.actor.id

    def profile(self, subject):
        return {**PROFILE, 'profile_completed_at': '2026-11-27T00:00:00Z'} if self.saved and subject == self.identity.actor.id else None

    def update(self, subject, profile):
        if subject != self.identity.actor.id: return False
        self.saved = profile
        return True


class OnboardingCredentials:
    def __init__(self, identity):
        self.identity = identity
        self.encoded = None

    def allow_attempt(self, mobile, ip): return True
    def find_actor(self, mobile): return self.identity.get_actor_by_mobile(mobile)
    def password_hash(self, subject): return self.encoded


def setup(pending=False):
    identity = FakeIdentity(Actor(uuid4(), Role.FARMER, AccountState.PENDING_APPROVAL if pending else AccountState.ACTIVE))
    otp = OnboardingOtp()
    onboarding = OnboardingStore(identity, otp, pending)
    credentials = OnboardingCredentials(identity)
    onboarding.credentials = credentials
    sessions = PasswordSessions()
    client = TestClient(create_app(identity_store=identity, otp_provider=otp,
        session_store=sessions, token_service=token_service(), farmer_onboarding=onboarding,
        credential_store=credentials))
    return client, identity, otp, onboarding


def test_registration_and_profile_authorization():
    client, identity, otp, onboarding = setup()
    requested = client.post('/api/v1/auth/farmer/register/request', json={'mobile_number': MOBILE})
    assert requested.status_code == 202 and requested.json()['challenge_id'] == str(otp.challenge)
    assert otp.purpose == 'REGISTRATION'
    invalid = {'challenge_id': str(otp.challenge), 'mobile_number': MOBILE, 'otp': '000000'}
    assert client.post('/api/v1/auth/farmer/register/verify', json=invalid).status_code == 401
    verified = client.post('/api/v1/auth/farmer/register/verify', json={**invalid, 'otp': '123456'})
    assert verified.status_code == 200
    assert client.post('/api/v1/auth/farmer/register/verify', json={**invalid, 'otp': '123456'}).status_code == 401
    body = {**PROFILE, 'onboarding_token': verified.json()['onboarding_token'],
        'password': 'StrongPassword123', 'confirm_password': 'StrongPassword123',
        'consent_document_id': 'dev-service', 'consent_version': 'dev-1',
        'acknowledge_required_consent': True}
    assert client.post('/api/v1/auth/farmer/register/complete', json={**body, 'acknowledge_required_consent': False}).status_code == 400
    response = client.post('/api/v1/auth/farmer/register/complete', json=body)
    assert response.status_code == 200
    assert client.post('/api/v1/auth/farmer/register/complete', json=body).status_code == 401
    headers = {'Authorization': 'Bearer '+response.json()['access_token']}
    assert client.get('/api/v1/farmer/profile', headers=headers).json()['full_name'] == PROFILE['full_name']
    assert client.get('/api/v1/farmer/onboarding/status', headers=headers).json()['status'] == 'complete'
    assert client.post('/api/v1/auth/password/login', json={'mobile_number': MOBILE, 'password': 'StrongPassword123'}).status_code == 200
    assert client.post('/api/v1/auth/otp/verify', json={'mobile': MOBILE, 'code': '123456'}).status_code == 200
    assert client.patch('/api/v1/farmer/profile', json={**PROFILE, 'role': 'admin'}, headers=headers).status_code == 200
    assert 'role' not in onboarding.saved
    assert client.get('/api/v1/farmer/profile').status_code == 401


def test_admin_prepared_identity_is_reused():
    client, identity, otp, onboarding = setup(pending=True)
    original = identity.actor.id
    assert client.post('/api/v1/auth/farmer/register/request', json={'mobile_number': MOBILE}).status_code == 202
    assert otp.purpose == 'ACCOUNT_CLAIM'
    verified = client.post('/api/v1/auth/farmer/register/verify', json={
        'challenge_id': str(otp.challenge), 'mobile_number': MOBILE, 'otp': '123456'})
    body = {**PROFILE, 'onboarding_token': verified.json()['onboarding_token'],
        'password': 'StrongPassword123', 'confirm_password': 'StrongPassword123',
        'consent_document_id': 'dev-service', 'consent_version': 'dev-1',
        'acknowledge_required_consent': True}
    assert client.post('/api/v1/auth/farmer/password/enroll', json=body).status_code == 200
    assert identity.actor.id == original
