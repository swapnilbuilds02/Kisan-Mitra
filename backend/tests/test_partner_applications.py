"""Shop/Consultant application and access gates with isolated adapters."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.identity import AccountState, Actor, Role
from backend.app.main import create_app
from backend.tests.key_material import token_service
from backend.tests.test_password_login import Credentials, PasswordSessions, MOBILE, PASSWORD
from backend.app.passwords import hash_password,verify_password
from backend.tests.test_auth_workflow import ProvisionedAdmins


class Identities:
    def __init__(self, role):
        self.partner=Actor(uuid4(),role,AccountState.PENDING_APPROVAL)
        self.admin=Actor(uuid4(),Role.ADMIN,AccountState.ACTIVE)
    def get_actor(self,user_id):
        for actor in (self.partner,self.admin):
            if actor.id==user_id: return actor
        return None
    def get_actor_by_mobile(self,mobile): return self.partner if mobile==MOBILE else None
    def claim_farmer(self,mobile): return None
    def ready(self): return True


class PartnerCredentials(Credentials):
    def __init__(self,identity,partners):
        super().__init__(identity)
        self.partners=partners
    def partner_status(self,subject): return self.partners.status if subject==self.identity.partner.id else None
    def complete_reset(self,digest,password):
        if digest!=getattr(self.partners.otp,'reset_digest',None): return False
        self.partners.otp.reset_digest=None
        self.encoded=hash_password(password)
        self.partners.sessions.revoke_user(self.identity.partner.id)
        return True
    def change_authenticated(self,subject,current_password,new_password):
        if subject!=self.identity.partner.id or not verify_password(current_password,self.encoded): return False
        self.encoded=hash_password(new_password)
        self.partners.sessions.revoke_user(subject)
        return True


class PartnerSessions(PasswordSessions):
    def create_partner(self,user_id,digest,ttl): return self.create(user_id,digest,ttl)


class PartnerOtp:
    def __init__(self):
        self.challenge=uuid4()
        self.used=False
    def ready(self): return True
    def request(self,mobile,ip): pass
    def verify(self,mobile,code): return False
    def request_partner(self,mobile,ip,role): return self.challenge
    def verify_partner(self,challenge,mobile,code,digest,role):
        if self.used or challenge!=self.challenge or code!='123456': return False
        self.used=True
        self.digest=digest
        self.role=role
        return True
    def request_purpose(self,mobile,ip,purpose,subject): return self.challenge
    def verify_partner_login(self,challenge,mobile,subject,code): return code=='123456' and challenge==self.challenge
    def request_partner_reset(self,mobile,ip,subject): return self.challenge
    def verify_reset(self,challenge,mobile,code,digest):
        if challenge!=self.challenge or mobile!=MOBILE or code!='123456': return False
        self.reset_digest=digest
        return True


class Partners:
    def __init__(self,identity,otp):
        self.identity=identity; self.otp=otp; self.status='pending_approval'; self.application=uuid4()
    def eligible(self,mobile): return mobile==MOBILE
    def complete(self,digest,password,role,profile):
        return self.identity.partner.id if self.otp.used and digest==self.otp.digest and role==self.identity.partner.role.value else None
    def state(self,user_id):
        if user_id!=self.identity.partner.id: return None
        return {'application_id':self.application,'partner_role':self.identity.partner.role.value,
            'status':self.status,'display_name':'Partner','preferred_language':'mr'}
    def pending(self,role): return [self.detail(self.application)] if self.status=='pending_approval' else []
    def detail(self,application_id):
        return {'application_id':application_id,'user_id':self.identity.partner.id,'status':self.status} if application_id==self.application else None
    def history(self,application_id): return []
    def application_for_user(self,user_id): return self.application if user_id==self.identity.partner.id else None
    def update(self,user_id,profile): return user_id==self.identity.partner.id
    def decision(self,application_id,operator_id,action,reason):
        if application_id!=self.application or operator_id!=self.identity.admin.id: return False
        transitions={('pending_approval','approve'):'approved',('pending_approval','reject'):'rejected',
            ('approved','suspend'):'suspended',('suspended','reactivate'):'approved'}
        result=transitions.get((self.status,action))
        if not result: return False
        self.status=result
        state={'approved':AccountState.ACTIVE,'rejected':AccountState.PENDING_APPROVAL,
            'suspended':AccountState.SUSPENDED}[result]
        self.identity.partner=Actor(self.identity.partner.id,self.identity.partner.role,state)
        self.sessions.revoke_user(self.identity.partner.id)
        return True


def setup(role):
    identity=Identities(role); otp=PartnerOtp(); partners=Partners(identity,otp)
    creds=PartnerCredentials(identity,partners); sessions=PartnerSessions(); tokens=token_service()
    partners.sessions=sessions
    client=TestClient(create_app(identity_store=identity,otp_provider=otp,session_store=sessions,
        credential_store=creds,partner_store=partners,token_service=tokens,admin_provisioning=ProvisionedAdmins()))
    return client,identity,otp,partners,sessions,tokens


def recent_admin_headers(tokens,identity,session_id):
    return {'Authorization':'Bearer '+tokens.issue_access(identity.admin.id,session_id),
            'X-Admin-Reauth':tokens.issue_admin_reauth(identity.admin.id,session_id)}


@pytest.mark.parametrize('role', [Role.SHOP,Role.CONSULTANT])
def test_partner_registration_pending_and_approval(role):
    client,identity,otp,partners,sessions,tokens=setup(role)
    base=f'/api/v1/auth/{role.value}/register'
    requested = client.post(base+'/request',json={'mobile_number':MOBILE})
    assert requested.status_code==202 and requested.json()['challenge_id']==str(otp.challenge)
    verified=client.post(base+'/verify',json={'challenge_id':str(otp.challenge),'mobile_number':MOBILE,'otp':'123456'})
    assert verified.status_code==200
    body=dict(onboarding_token=verified.json()['onboarding_token'],password=PASSWORD,confirm_password=PASSWORD,
        display_name='Partner Name',preferred_language='mr',state='Maharashtra',district='District',taluka='Taluka',
        locality='Village',consent_document_id='dev-partner',consent_version='dev-1',acknowledge_required_consent=True)
    assert client.post(base+'/complete',json=body).json()['status']=='pending_approval'
    login=client.post('/api/v1/auth/password/login',json={'mobile_number':MOBILE,'password':PASSWORD})
    assert login.status_code==200
    headers={'Authorization':'Bearer '+login.json()['access_token']}
    assert client.get(f'/api/v1/{role.value}/application/status',headers=headers).json()['status']=='pending_approval'
    assert client.get('/api/v1/auth/session',headers=headers).json()['account_state']=='pending_approval'
    assert client.get('/api/v1/partner/overview',headers=headers).status_code==403
    assert client.get('/api/v1/admin/partner-applications',headers=headers).status_code==403
    admin_session=sessions.create(identity.admin.id,'a'*64,600)
    admin_headers=recent_admin_headers(tokens,identity,admin_session)
    assert client.post(f'/api/v1/admin/partner-applications/{partners.application}/approve',
        json={'reason':'Reviewed application'},headers=admin_headers).status_code==200
    assert client.get('/api/v1/partner/overview',headers=headers).status_code!=200
    fresh=client.post('/api/v1/auth/password/login',json={'mobile_number':MOBILE,'password':PASSWORD})
    assert fresh.status_code==200
    assert client.get('/api/v1/partner/overview',headers={'Authorization':'Bearer '+fresh.json()['access_token']}).status_code==200


@pytest.mark.parametrize('role',[Role.SHOP,Role.CONSULTANT])
def test_partner_otp_login_and_suspension(role):
    client,identity,otp,partners,sessions,tokens=setup(role)
    partners.status='approved'
    identity.partner=Actor(identity.partner.id,role,AccountState.ACTIVE)
    requested=client.post('/api/v1/auth/partner/otp/request',json={'mobile_number':MOBILE})
    assert requested.status_code==202
    verified=client.post('/api/v1/auth/partner/otp/verify',json={
        'challenge_id':requested.json()['challenge_id'],'mobile_number':MOBILE,'otp':'123456'})
    assert verified.status_code==200
    headers={'Authorization':'Bearer '+verified.json()['access_token']}
    assert client.get('/api/v1/partner/overview',headers=headers).status_code==200
    admin_session=sessions.create(identity.admin.id,'a'*64,600)
    admin_headers=recent_admin_headers(tokens,identity,admin_session)
    assert client.post(f'/api/v1/admin/partners/{identity.partner.id}/suspend',
        json={'reason':'Security review'},headers=admin_headers).status_code==200
    assert client.get('/api/v1/partner/overview',headers=headers).status_code==401
    assert client.post('/api/v1/auth/refresh',json={'refresh_token':verified.json()['refresh_token']}).status_code==401
    assert client.post('/api/v1/auth/password/login',json={'mobile_number':MOBILE,'password':PASSWORD}).status_code==401
    assert client.post(f'/api/v1/admin/partners/{identity.partner.id}/reactivate',
        json={'reason':'Review complete'},headers=admin_headers).status_code==200
    assert client.post('/api/v1/auth/password/login',json={'mobile_number':MOBILE,'password':PASSWORD}).status_code==200


@pytest.mark.parametrize('role',[Role.SHOP,Role.CONSULTANT])
def test_partner_recovery_change_refresh_and_logout(role):
    client,identity,otp,partners,sessions,tokens=setup(role)
    assert client.post('/api/v1/auth/password/forgot',json={'mobile_number':MOBILE}).status_code==202
    verified=client.post('/api/v1/auth/password/reset/verify',json={
        'challenge_id':str(otp.challenge),'mobile_number':MOBILE,'otp':'123456'})
    assert verified.status_code==200
    assert client.post('/api/v1/auth/password/reset',json={'reset_token':verified.json()['reset_token'],
        'new_password':'NewPartnerPassword123','confirm_password':'NewPartnerPassword123'}).status_code==204
    assert client.post('/api/v1/auth/password/login',json={'mobile_number':MOBILE,'password':PASSWORD}).status_code==401
    login=client.post('/api/v1/auth/password/login',json={'mobile_number':MOBILE,'password':'NewPartnerPassword123'})
    assert login.status_code==200
    refreshed=client.post('/api/v1/auth/refresh',json={'refresh_token':login.json()['refresh_token']})
    assert refreshed.status_code==200
    headers={'Authorization':'Bearer '+refreshed.json()['access_token']}
    assert client.post('/api/v1/auth/password/change',json={'current_password':'NewPartnerPassword123',
        'new_password':'ChangedPartnerPassword123','confirm_password':'ChangedPartnerPassword123'},headers=headers).status_code==204
    assert client.get(f'/api/v1/{role.value}/application/status',headers=headers).status_code==401
    fresh=client.post('/api/v1/auth/password/login',json={'mobile_number':MOBILE,'password':'ChangedPartnerPassword123'})
    assert fresh.status_code==200
    assert client.post('/api/v1/auth/logout',headers={'Authorization':'Bearer '+fresh.json()['access_token']}).status_code==204


@pytest.mark.parametrize('role',[Role.SHOP,Role.CONSULTANT])
def test_rejection_has_no_privileged_access(role):
    client,identity,otp,partners,sessions,tokens=setup(role)
    pending=client.post('/api/v1/auth/password/login',json={'mobile_number':MOBILE,'password':PASSWORD})
    assert pending.status_code==200
    admin_session=sessions.create(identity.admin.id,'a'*64,600)
    admin_headers=recent_admin_headers(tokens,identity,admin_session)
    assert client.post(f'/api/v1/admin/partner-applications/{partners.application}/reject',
        json={'reason':'Incomplete application'},headers=admin_headers).status_code==200
    assert client.post('/api/v1/auth/password/login',json={'mobile_number':MOBILE,'password':PASSWORD}).status_code==401
    assert client.get('/api/v1/partner/overview',headers={
        'Authorization':'Bearer '+pending.json()['access_token']}).status_code==401
    assert client.post(f'/api/v1/admin/partners/{identity.partner.id}/reactivate',
        json={'reason':'Unauthorized transition'},headers=admin_headers).status_code==409
