"""Kisan Mitra Phase 1 API shell.

No public farmer feature is mounted here. The shell proves token validation,
server-side role lookup, and denial behavior before later routes are added.
"""

from __future__ import annotations

import os
import hashlib
import secrets
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .auth import (
    AUDIENCE, ISSUER, AuthWorkflow, AuthenticationError, OtpProvider,
    SessionStore, TokenService, UnavailableOtpProvider, UnavailableSessionStore,
)

from .identity import (
    AccountState,
    Actor,
    IdentityStore,
    PostgresIdentityStore,
    Role,
    UnavailableIdentityStore,
    normalize_mobile,
)
from .postgres_auth import PostgresSessionStore
from .credentials import PostgresCredentialStore
from .farmer_onboarding import PostgresFarmerOnboarding
from .partners import PostgresPartnerStore
from .admin_provision import PostgresAdminProvisioning
from .plots import PostgresPlotStore
from .weather import WeatherContextService
from .auth import REFRESH_TTL_SECONDS, _digest

bearer = HTTPBearer(auto_error=False)


class OtpRequest(BaseModel):
    mobile: str

    @field_validator("mobile")
    @classmethod
    def canonical_mobile(cls, value: str) -> str:
        return normalize_mobile(value)


class OtpVerification(OtpRequest):
    code: str = Field(pattern=r"^[0-9]{6}$")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=50, max_length=256)


class FarmerPreparation(OtpRequest):
    reason: str = Field(min_length=5, max_length=500)


class PasswordLogin(BaseModel):
    mobile_number: str
    password: str = Field(min_length=1, max_length=1024)

    @field_validator('mobile_number')
    @classmethod
    def canonical_mobile(cls, value: str) -> str:
        return normalize_mobile(value)


class ResetVerify(BaseModel):
    challenge_id: UUID
    mobile_number: str
    otp: str = Field(pattern=r'^[0-9]{6}$')

    @field_validator('mobile_number')
    @classmethod
    def canonical_mobile(cls, value: str) -> str:
        return normalize_mobile(value)


class PasswordLoginForgot(BaseModel):
    mobile_number: str

    @field_validator('mobile_number')
    @classmethod
    def canonical_mobile(cls, value: str) -> str:
        return normalize_mobile(value)


class ResetComplete(BaseModel):
    reset_token: str = Field(min_length=40, max_length=256)
    new_password: str
    confirm_password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


class AdminReauth(BaseModel):
    current_password: str = Field(min_length=1,max_length=1024)


class FarmerRegisterVerify(BaseModel):
    challenge_id: UUID
    mobile_number: str
    otp: str = Field(pattern=r'^[0-9]{6}$')

    @field_validator('mobile_number')
    @classmethod
    def canonical_mobile(cls, value: str) -> str:
        return normalize_mobile(value)


class FarmerProfileInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    preferred_language: str = Field(pattern=r'^(mr|en)$')
    village: str = Field(min_length=1, max_length=100)
    taluka: str = Field(min_length=1, max_length=100)
    district: str = Field(min_length=1, max_length=100)
    state: str = Field(default='Maharashtra', min_length=1, max_length=100)
    pincode: str | None = Field(default=None, pattern=r'^[0-9]{6}$')


class FarmerRegisterComplete(FarmerProfileInput):
    onboarding_token: str = Field(min_length=40, max_length=256)
    password: str
    confirm_password: str
    consent_document_id: str = Field(min_length=1, max_length=100)
    consent_version: str = Field(min_length=1, max_length=50)
    acknowledge_required_consent: bool


class PartnerComplete(BaseModel):
    onboarding_token: str = Field(min_length=40,max_length=256)
    password: str
    confirm_password: str
    display_name: str = Field(min_length=2,max_length=150)
    representative_name: str | None = Field(default=None,max_length=150)
    specialization: str | None = Field(default=None,max_length=150)
    organization_name: str | None = Field(default=None,max_length=150)
    preferred_language: str = Field(pattern=r'^(mr|en)$')
    state: str = Field(min_length=1,max_length=100)
    district: str = Field(min_length=1,max_length=100)
    taluka: str = Field(min_length=1,max_length=100)
    locality: str = Field(min_length=1,max_length=100)
    address: str | None = Field(default=None,max_length=300)
    pincode: str | None = Field(default=None,pattern=r'^[0-9]{6}$')
    consent_document_id: str = Field(min_length=1,max_length=100)
    consent_version: str = Field(min_length=1,max_length=50)
    acknowledge_required_consent: bool


class PartnerProfileUpdate(BaseModel):
    preferred_language: str = Field(pattern=r'^(mr|en)$')
    state: str = Field(min_length=1,max_length=100)
    district: str = Field(min_length=1,max_length=100)
    taluka: str = Field(min_length=1,max_length=100)
    locality: str = Field(min_length=1,max_length=100)
    address: str | None = Field(default=None,max_length=300)
    pincode: str | None = Field(default=None,pattern=r'^[0-9]{6}$')


class PartnerDecision(BaseModel):
    reason: str = Field(min_length=5,max_length=500)


class AdminActivate(BaseModel):
    onboarding_token: str = Field(min_length=40,max_length=256)
    password: str
    confirm_password: str


class PlotInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    plot_name: str = Field(min_length=2, max_length=120)
    crop_type: str = Field(default='grape', pattern=r'^[a-z][a-z0-9_]{1,39}$')
    grape_variety: str | None = Field(default=None, max_length=120)
    area: Decimal = Field(gt=0, le=1000000, max_digits=12, decimal_places=3)
    area_unit: str = Field(pattern=r'^(acre|hectare|sq_m)$')
    village: str = Field(min_length=1, max_length=100)
    taluka: str = Field(min_length=1, max_length=100)
    district: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, max_digits=9, decimal_places=6)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, max_digits=9, decimal_places=6)
    location_permission: bool = False
    pruning_date: date | None = None
    current_crop_stage: str = Field(default='not_set', pattern=r'^[a-z][a-z0-9_]{1,39}$')
    preferred_language: str = Field(default='mr', pattern=r'^(mr|en)$')

    @model_validator(mode='after')
    def validate_plot(self):
        if not all((self.plot_name.strip(), self.village.strip(), self.taluka.strip(),
                    self.district.strip(), self.state.strip())):
            raise ValueError('Plot name and location are required')
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError('Coordinates must be supplied together')
        if self.latitude is not None and not self.location_permission:
            raise ValueError('Precise location requires Farmer permission')
        if self.pruning_date and self.pruning_date > date.today():
            raise ValueError('Pruning date cannot be in the future')
        return self


class PlotUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    plot_name: str | None = None
    crop_type: str | None = None
    grape_variety: str | None = None
    area: Decimal | None = None
    area_unit: str | None = None
    village: str | None = None
    taluka: str | None = None
    district: str | None = None
    state: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    location_permission: bool | None = None
    pruning_date: date | None = None
    current_crop_stage: str | None = None
    preferred_language: str | None = None


def create_app(
    *,
    identity_store: IdentityStore | None = None,
    token_service: TokenService | None = None,
    otp_provider: OtpProvider | None = None,
    session_store: SessionStore | None = None,
    credential_store=None,
    farmer_onboarding=None,
    partner_store=None,
    admin_provisioning=None,
    plot_store=None,
    weather_service=None,
) -> FastAPI:
    """Build the app with explicit dependencies for local/API tests.

    A configured API requires a secret and database. Missing configuration
    leaves health endpoints available but protected routes fail closed.
    """

    tokens = token_service or TokenService.from_environment()
    database_url = os.getenv("DATABASE_URL", "")
    if identity_store is None:
        identity_store = (
            PostgresIdentityStore(database_url)
            if database_url
            else UnavailableIdentityStore()
        )
    store = identity_store
    otp = otp_provider or UnavailableOtpProvider()
    sessions = session_store or (PostgresSessionStore(database_url) if database_url else UnavailableSessionStore())
    workflow = AuthWorkflow(store, otp, sessions, tokens) if tokens else None
    credentials = credential_store or (PostgresCredentialStore(store, os.getenv('PASSWORD_RATE_PEPPER', ''))
        if isinstance(store, PostgresIdentityStore) and os.getenv('PASSWORD_RATE_PEPPER') else None)
    onboarding = farmer_onboarding or (PostgresFarmerOnboarding(store) if isinstance(store, PostgresIdentityStore) else None)
    partners = partner_store or (PostgresPartnerStore(store) if isinstance(store, PostgresIdentityStore) else None)
    admins = admin_provisioning or (PostgresAdminProvisioning(store) if isinstance(store, PostgresIdentityStore) else None)
    plots = plot_store or (PostgresPlotStore(store) if isinstance(store, PostgresIdentityStore) else None)
    weather = weather_service or WeatherContextService()
    app = FastAPI(title="Kisan Mitra API", version="0.1.0")

    def session_actor(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> Actor:
        if credentials is None:
            raise HTTPException(status_code=401, detail="AUTH_REQUIRED")
        if tokens is None:
            raise HTTPException(status_code=503, detail="AUTH_NOT_CONFIGURED")
        try:
            identity = tokens.decode_access(credentials.credentials)
        except AuthenticationError as exc:
            raise HTTPException(status_code=401, detail="INVALID_TOKEN") from exc

        try:
            if not sessions.active(identity.user_id, identity.session_id):
                raise HTTPException(status_code=401, detail="SESSION_REVOKED")
            actor = store.get_actor(identity.user_id)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=503, detail="AUTH_BACKEND_UNAVAILABLE") from exc
        if actor is None:
            raise HTTPException(status_code=401, detail="UNKNOWN_USER")
        if actor.role in (Role.ADMIN,Role.SUPER_ADMIN):
            try:
                if admins is None or not admins.active(actor.id):
                    raise HTTPException(status_code=401,detail='ADMIN_NOT_PROVISIONED')
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(status_code=503,detail='AUTH_BACKEND_UNAVAILABLE') from exc
        return actor

    def current_actor(actor: Actor = Depends(session_actor)) -> Actor:
        if actor.state != AccountState.ACTIVE:
            details = {
                AccountState.SUSPENDED: "ACCOUNT_SUSPENDED",
                AccountState.PENDING_APPROVAL: "PENDING_APPROVAL",
                AccountState.EXPIRED: "SUBSCRIPTION_EXPIRED",
            }
            raise HTTPException(status_code=403, detail=details[actor.state])
        return actor

    def applicant_actor(actor: Actor = Depends(session_actor)) -> Actor:
        if actor.role not in (Role.SHOP,Role.CONSULTANT) or actor.state not in (AccountState.ACTIVE,AccountState.PENDING_APPROVAL):
            raise HTTPException(status_code=403,detail='ROLE_FORBIDDEN')
        if partners is None:
            raise HTTPException(status_code=503,detail='PARTNER_UNAVAILABLE')
        state = partners.state(actor.id)
        if state is None or (state['status'],actor.state) not in (
            ('pending_approval',AccountState.PENDING_APPROVAL),('approved',AccountState.ACTIVE)):
            raise HTTPException(status_code=403,detail='PARTNER_NOT_ELIGIBLE')
        return actor

    def require_roles(*allowed: Role):
        def dependency(actor: Actor = Depends(current_actor)) -> Actor:
            if actor.role not in allowed:
                raise HTTPException(status_code=403, detail="ROLE_FORBIDDEN")
            return actor

        return dependency

    def require_recent_admin(
        actor: Actor = Depends(require_roles(Role.ADMIN,Role.SUPER_ADMIN)),
        bearer_credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
        proof: str | None = Header(default=None,alias='X-Admin-Reauth'),
    ) -> Actor:
        if tokens is None or bearer_credentials is None or not proof:
            raise HTTPException(status_code=403,detail='RECENT_AUTH_REQUIRED')
        try:
            access=tokens.decode_access(bearer_credentials.credentials)
            recent=tokens.decode_admin_reauth(proof)
        except AuthenticationError:
            raise HTTPException(status_code=403,detail='RECENT_AUTH_REQUIRED')
        if recent.user_id != actor.id or recent.session_id != access.session_id:
            raise HTTPException(status_code=403,detail='RECENT_AUTH_REQUIRED')
        return actor

    @app.get("/health/live")
    def liveness() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/health/ready")
    def readiness() -> dict[str, str]:
        try:
            ready = tokens is not None and store.ready() and otp.ready() and sessions.ready()
        except Exception:
            ready = False
        if not ready:
            raise HTTPException(status_code=503, detail="NOT_READY")
        return {"status": "ready"}

    @app.get("/api/v1/users/me/profile")
    def profile(actor: Actor = Depends(current_actor)) -> dict[str, str]:
        return {
            "id": str(actor.id),
            "role": actor.role.value,
            "account_state": actor.state.value,
            "account_tier": actor.account_tier,
        }

    @app.get('/api/v1/auth/session')
    def session_profile(actor: Actor = Depends(session_actor)) -> dict[str,str]:
        if actor.state == AccountState.PENDING_APPROVAL:
            if actor.role not in (Role.SHOP,Role.CONSULTANT) or partners is None:
                raise HTTPException(status_code=403,detail='PENDING_APPROVAL')
            state = partners.state(actor.id)
            if state is None or state['status'] != 'pending_approval':
                raise HTTPException(status_code=403,detail='PARTNER_NOT_ELIGIBLE')
        elif actor.state != AccountState.ACTIVE:
            raise HTTPException(status_code=403,detail='ACCOUNT_NOT_ACTIVE')
        return {'id':str(actor.id),'role':actor.role.value,
                'account_state':actor.state.value,'account_tier':actor.account_tier}

    @app.post("/api/v1/auth/otp/request", status_code=202)
    def request_otp(body: OtpRequest, request: Request) -> dict[str, str]:
        if workflow is None:
            raise HTTPException(status_code=503, detail="AUTH_NOT_CONFIGURED")
        try:
            workflow.request_otp(body.mobile, request.client.host if request.client else "unknown")
        except Exception as exc:
            raise HTTPException(status_code=503, detail="OTP_UNAVAILABLE") from exc
        return {"status": "accepted"}

    @app.post('/api/v1/auth/password/login')
    def password_login(body: PasswordLogin, request: Request, response: Response) -> dict[str, str | int]:
        if workflow is None or credentials is None:
            raise HTTPException(status_code=503, detail='AUTH_NOT_CONFIGURED')
        try:
            pair = workflow.login_password(body.mobile_number, body.password,
                request.client.host if request.client else 'unknown', credentials)
        except AuthenticationError as exc:
            raise HTTPException(status_code=401, detail='INVALID_CREDENTIALS') from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail='AUTH_BACKEND_UNAVAILABLE') from exc
        response.headers['Cache-Control'] = 'no-store'
        return pair

    @app.post('/api/v1/auth/password/forgot', status_code=202)
    def forgot_password(body: PasswordLoginForgot, request: Request, response: Response) -> dict[str, str]:
        if credentials is None or not hasattr(otp, 'request_purpose'):
            raise HTTPException(status_code=503, detail='AUTH_NOT_CONFIGURED')
        challenge=uuid4()
        try:
            actor = credentials.find_actor(body.mobile_number)
            has_password = bool(credentials.password_hash(actor.id if actor else UUID(int=0)))
            farmer_eligible = actor and actor.role == Role.FARMER and actor.state == AccountState.ACTIVE and has_password
            partner_state = partners.state(actor.id) if actor and actor.role in (Role.SHOP,Role.CONSULTANT) and partners else None
            partner_eligible = actor and has_password and partner_state and (partner_state['status'],actor.state) in (
                ('pending_approval',AccountState.PENDING_APPROVAL),('approved',AccountState.ACTIVE))
            peer = request.client.host if request.client else 'unknown'
            admin_eligible = actor and actor.role in (Role.ADMIN,Role.SUPER_ADMIN) and actor.state == AccountState.ACTIVE and has_password and admins and admins.active(actor.id)
            if admin_eligible and hasattr(otp,'request_admin_reset') and hasattr(otp,'allow_admin_attempt') and otp.allow_admin_attempt(body.mobile_number,peer):
                challenge=otp.request_admin_reset(body.mobile_number,peer,actor.id) or challenge
            elif partner_eligible and hasattr(otp,'request_partner_reset'):
                challenge=otp.request_partner_reset(body.mobile_number,peer,actor.id) or challenge
            else:
                challenge=otp.request_purpose(body.mobile_number,peer,'PASSWORD_RESET',actor.id if farmer_eligible else None) or challenge
        except Exception:
            # Provider failures and unknown accounts share the public response.
            pass
        response.headers['Cache-Control'] = 'no-store'
        return {'status': 'accepted','challenge_id':str(challenge)}

    @app.post('/api/v1/auth/admin/activate/request',status_code=202)
    def admin_activate_request(body: PasswordLoginForgot,request: Request) -> dict[str,str]:
        if admins is None or not hasattr(otp,'request_purpose'):
            raise HTTPException(status_code=503,detail='AUTH_NOT_CONFIGURED')
        challenge=uuid4()
        try:
            subject=admins.candidate(body.mobile_number)
            if subject and hasattr(otp,'allow_admin_attempt') and otp.allow_admin_attempt(body.mobile_number,
                request.client.host if request.client else 'unknown'):
                challenge=otp.request_purpose(body.mobile_number,
                    request.client.host if request.client else 'unknown','ACCOUNT_CLAIM',subject) or challenge
        except Exception:
            pass
        return {'status':'accepted','challenge_id':str(challenge)}

    @app.post('/api/v1/auth/admin/activate/verify')
    def admin_activate_verify(body: FarmerRegisterVerify,response: Response) -> dict[str,str]:
        if not hasattr(otp,'verify_admin_onboarding'):
            raise HTTPException(status_code=503,detail='AUTH_NOT_CONFIGURED')
        secret=secrets.token_urlsafe(32)
        try:
            valid=otp.verify_admin_onboarding(body.challenge_id,body.mobile_number,body.otp,_digest(secret))
        except Exception:
            valid=False
        if not valid:
            raise HTTPException(status_code=401,detail='INVALID_ONBOARDING_CHALLENGE')
        response.headers['Cache-Control']='no-store'
        return {'onboarding_token':secret}

    @app.post('/api/v1/auth/admin/activate/complete',status_code=204)
    def admin_activate_complete(body: AdminActivate) -> None:
        if admins is None:
            raise HTTPException(status_code=503,detail='AUTH_NOT_CONFIGURED')
        if body.password!=body.confirm_password:
            raise HTTPException(status_code=400,detail='PASSWORD_CONFIRMATION_MISMATCH')
        from .passwords import validate_password
        try:
            validate_password(body.password)
        except ValueError:
            raise HTTPException(status_code=400,detail='WEAK_PASSWORD')
        try:
            activated=admins.activate(_digest(body.onboarding_token),body.password)
        except Exception as exc:
            raise HTTPException(status_code=503,detail='AUTH_BACKEND_UNAVAILABLE') from exc
        if not activated:
            raise HTTPException(status_code=401,detail='INVALID_ONBOARDING_AUTHORIZATION')

    @app.post('/api/v1/auth/admin/otp/request',status_code=202)
    def admin_otp_request(body: PasswordLoginForgot,request: Request) -> dict[str,str]:
        if admins is None or not hasattr(otp,'request_purpose'):
            raise HTTPException(status_code=503,detail='AUTH_NOT_CONFIGURED')
        challenge=uuid4()
        try:
            if not hasattr(otp,'allow_admin_attempt') or not otp.allow_admin_attempt(body.mobile_number,
                request.client.host if request.client else 'unknown'):
                return {'status':'accepted','challenge_id':str(challenge)}
            actor=store.get_actor_by_mobile(body.mobile_number)
            if actor and actor.role in (Role.ADMIN,Role.SUPER_ADMIN) and actor.state==AccountState.ACTIVE and admins.active(actor.id):
                challenge=otp.request_purpose(body.mobile_number,
                    request.client.host if request.client else 'unknown','LOGIN',actor.id) or challenge
        except Exception:
            pass
        return {'status':'accepted','challenge_id':str(challenge)}

    @app.post('/api/v1/auth/admin/otp/verify')
    def admin_otp_verify(body: FarmerRegisterVerify,response: Response) -> dict[str,str|int]:
        if workflow is None or admins is None or not hasattr(otp,'verify_admin_login') or not hasattr(sessions,'create_admin'):
            raise HTTPException(status_code=503,detail='AUTH_NOT_CONFIGURED')
        try:
            actor=store.get_actor_by_mobile(body.mobile_number)
            if actor is None or actor.role not in (Role.ADMIN,Role.SUPER_ADMIN) or actor.state!=AccountState.ACTIVE or not admins.active(actor.id):
                raise ValueError('Invalid account')
            if not otp.verify_admin_login(body.challenge_id,body.mobile_number,actor.id,body.otp):
                raise ValueError('Invalid code')
            secret=secrets.token_urlsafe(32)
            session_id=sessions.create_admin(actor.id,_digest(secret),REFRESH_TTL_SECONDS)
            if session_id is None:
                raise ValueError('Invalid account')
            pair=workflow._pair(actor,session_id,f'{session_id}.{secret}')
        except Exception:
            raise HTTPException(status_code=401,detail='INVALID_CREDENTIALS')
        response.headers['Cache-Control']='no-store'
        return pair

    @app.post('/api/v1/auth/farmer/register/request', status_code=202)
    def farmer_register_request(body: PasswordLoginForgot, request: Request) -> dict[str, str]:
        if onboarding is None or not hasattr(otp, 'request_purpose'):
            raise HTTPException(status_code=503, detail='AUTH_NOT_CONFIGURED')
        challenge=uuid4()
        try:
            target = onboarding.target(body.mobile_number)
            if target:
                subject, purpose = target
                challenge=otp.request_purpose(body.mobile_number, request.client.host if request.client else 'unknown', purpose, subject) or challenge
        except Exception:
            pass
        return {'status': 'accepted', 'challenge_id':str(challenge)}

    @app.post('/api/v1/auth/farmer/register/verify')
    def farmer_register_verify(body: FarmerRegisterVerify, response: Response) -> dict[str, str]:
        if not hasattr(otp, 'verify_onboarding'):
            raise HTTPException(status_code=503, detail='AUTH_NOT_CONFIGURED')
        secret = secrets.token_urlsafe(32)
        try:
            valid = otp.verify_onboarding(body.challenge_id, body.mobile_number, body.otp, _digest(secret))
        except Exception:
            valid = False
        if not valid:
            raise HTTPException(status_code=401, detail='INVALID_ONBOARDING_CHALLENGE')
        response.headers['Cache-Control'] = 'no-store'
        return {'onboarding_token': secret}

    @app.post('/api/v1/auth/farmer/register/complete')
    @app.post('/api/v1/auth/farmer/password/enroll')
    def farmer_register_complete(body: FarmerRegisterComplete, response: Response) -> dict[str, str | int]:
        if onboarding is None or workflow is None:
            raise HTTPException(status_code=503, detail='AUTH_NOT_CONFIGURED')
        if body.password != body.confirm_password:
            raise HTTPException(status_code=400, detail='PASSWORD_CONFIRMATION_MISMATCH')
        if not body.acknowledge_required_consent:
            raise HTTPException(status_code=400, detail='CONSENT_REQUIRED')
        from .passwords import validate_password
        try:
            validate_password(body.password)
        except ValueError:
            raise HTTPException(status_code=400, detail='WEAK_PASSWORD')
        try:
            farmer_id = onboarding.complete(_digest(body.onboarding_token), body.password, body.model_dump())
        except Exception:
            raise HTTPException(status_code=503, detail='ONBOARDING_UNAVAILABLE')
        if farmer_id is None:
            raise HTTPException(status_code=401, detail='INVALID_ONBOARDING_AUTHORIZATION')
        try:
            session_secret = secrets.token_urlsafe(32)
            session_id = sessions.create(farmer_id, _digest(session_secret), REFRESH_TTL_SECONDS)
            actor = store.get_actor(farmer_id)
            if actor is None or actor.role != Role.FARMER or actor.state != AccountState.ACTIVE:
                raise RuntimeError('Activation failed')
            pair = workflow._pair(actor, session_id, f'{session_id}.{session_secret}')
        except Exception:
            raise HTTPException(status_code=503, detail='SESSION_UNAVAILABLE')
        response.headers['Cache-Control'] = 'no-store'
        return pair

    @app.post('/api/v1/auth/{partner_role}/register/request', status_code=202)
    def partner_register_request(partner_role: str,body: PasswordLoginForgot,request: Request) -> dict[str,str]:
        if partner_role not in ('shop','consultant'):
            raise HTTPException(status_code=404,detail='NOT_FOUND')
        if partners is None or not hasattr(otp,'request_partner'):
            raise HTTPException(status_code=503,detail='AUTH_NOT_CONFIGURED')
        challenge=uuid4()
        try:
            if partners.eligible(body.mobile_number):
                challenge=otp.request_partner(body.mobile_number,request.client.host if request.client else 'unknown',partner_role) or challenge
        except Exception:
            pass
        return {'status':'accepted','challenge_id':str(challenge)}

    @app.post('/api/v1/auth/{partner_role}/register/verify')
    def partner_register_verify(partner_role: str,body: FarmerRegisterVerify,response: Response) -> dict[str,str]:
        if partner_role not in ('shop','consultant'):
            raise HTTPException(status_code=404,detail='NOT_FOUND')
        if not hasattr(otp,'verify_partner'):
            raise HTTPException(status_code=503,detail='AUTH_NOT_CONFIGURED')
        secret=secrets.token_urlsafe(32)
        try:
            valid=otp.verify_partner(body.challenge_id,body.mobile_number,body.otp,_digest(secret),partner_role)
        except Exception:
            valid=False
        if not valid:
            raise HTTPException(status_code=401,detail='INVALID_ONBOARDING_CHALLENGE')
        response.headers['Cache-Control']='no-store'
        return {'onboarding_token':secret}

    @app.post('/api/v1/auth/{partner_role}/register/complete',status_code=201)
    def partner_register_complete(partner_role: str,body: PartnerComplete) -> dict[str,str]:
        if partner_role not in ('shop','consultant'):
            raise HTTPException(status_code=404,detail='NOT_FOUND')
        if partners is None:
            raise HTTPException(status_code=503,detail='PARTNER_UNAVAILABLE')
        if body.password!=body.confirm_password:
            raise HTTPException(status_code=400,detail='PASSWORD_CONFIRMATION_MISMATCH')
        if not body.acknowledge_required_consent:
            raise HTTPException(status_code=400,detail='CONSENT_REQUIRED')
        from .passwords import validate_password
        try:
            validate_password(body.password)
        except ValueError:
            raise HTTPException(status_code=400,detail='WEAK_PASSWORD')
        try:
            user_id=partners.complete(_digest(body.onboarding_token),body.password,partner_role,body.model_dump())
        except Exception:
            raise HTTPException(status_code=503,detail='APPLICATION_UNAVAILABLE')
        if user_id is None:
            raise HTTPException(status_code=401,detail='INVALID_ONBOARDING_AUTHORIZATION')
        return {'status':'pending_approval'}

    @app.post('/api/v1/auth/partner/otp/request',status_code=202)
    def partner_otp_request(body: PasswordLoginForgot,request: Request) -> dict[str,str]:
        if partners is None or not hasattr(otp,'request_purpose'):
            raise HTTPException(status_code=503,detail='AUTH_NOT_CONFIGURED')
        challenge=uuid4()
        try:
            actor=store.get_actor_by_mobile(body.mobile_number)
            if actor and actor.role in (Role.SHOP,Role.CONSULTANT):
                state=partners.state(actor.id)
                if state and (state['status'],actor.state) in (
                    ('pending_approval',AccountState.PENDING_APPROVAL),('approved',AccountState.ACTIVE)):
                    challenge=otp.request_purpose(body.mobile_number,
                        request.client.host if request.client else 'unknown','LOGIN',actor.id) or challenge
        except Exception:
            pass
        return {'status':'accepted','challenge_id':str(challenge)}

    @app.post('/api/v1/auth/partner/otp/verify')
    def partner_otp_verify(body: FarmerRegisterVerify,response: Response) -> dict[str,str|int]:
        if workflow is None or partners is None or not hasattr(otp,'verify_partner_login') or not hasattr(sessions,'create_partner'):
            raise HTTPException(status_code=503,detail='AUTH_NOT_CONFIGURED')
        try:
            actor=store.get_actor_by_mobile(body.mobile_number)
            if actor is None or actor.role not in (Role.SHOP,Role.CONSULTANT):
                raise ValueError('Invalid account')
            state=partners.state(actor.id)
            if state is None or (state['status'],actor.state) not in (
                ('pending_approval',AccountState.PENDING_APPROVAL),('approved',AccountState.ACTIVE)):
                raise ValueError('Invalid account')
            if not otp.verify_partner_login(body.challenge_id,body.mobile_number,actor.id,body.otp):
                raise ValueError('Invalid code')
            secret=secrets.token_urlsafe(32)
            session_id=sessions.create_partner(actor.id,_digest(secret),REFRESH_TTL_SECONDS)
            if session_id is None:
                raise ValueError('Invalid account')
            pair=workflow._pair(actor,session_id,f'{session_id}.{secret}')
        except Exception:
            raise HTTPException(status_code=401,detail='INVALID_CREDENTIALS')
        response.headers['Cache-Control']='no-store'
        return pair

    @app.get('/api/v1/farmer/profile')
    def farmer_profile(actor: Actor = Depends(require_roles(Role.FARMER))) -> dict:
        if onboarding is None:
            raise HTTPException(status_code=503, detail='PROFILE_UNAVAILABLE')
        result = onboarding.profile(actor.id)
        if result is None:
            raise HTTPException(status_code=404, detail='PROFILE_INCOMPLETE')
        return result

    @app.patch('/api/v1/farmer/profile')
    def update_farmer_profile(body: FarmerProfileInput, actor: Actor = Depends(require_roles(Role.FARMER))) -> dict[str, str]:
        if onboarding is None or not onboarding.update(actor.id, body.model_dump()):
            raise HTTPException(status_code=404, detail='PROFILE_INCOMPLETE')
        return {'status': 'updated'}

    @app.get('/api/v1/farmer/onboarding/status')
    def farmer_onboarding_status(actor: Actor = Depends(require_roles(Role.FARMER))) -> dict[str, str]:
        profile = onboarding.profile(actor.id) if onboarding else None
        return {'status': 'complete' if profile and profile.get('profile_completed_at') else 'incomplete'}

    def plot_repository():
        if plots is None:
            raise HTTPException(status_code=503, detail='PLOTS_UNAVAILABLE')
        return plots

    @app.post('/api/v1/farmer/plots', status_code=201)
    def create_plot(body: PlotInput, actor: Actor = Depends(require_roles(Role.FARMER))) -> dict:
        repository = plot_repository()
        try:
            plot_id = repository.create(actor.id, body.model_dump())
        except Exception as exc:
            raise HTTPException(status_code=503, detail='PLOTS_UNAVAILABLE') from exc
        if plot_id is None:
            raise HTTPException(status_code=409, detail='PLOT_CREATE_DENIED')
        return repository.get(actor.id, plot_id)

    @app.get('/api/v1/farmer/plots')
    def list_plots(actor: Actor = Depends(require_roles(Role.FARMER))) -> list[dict]:
        return plot_repository().list(actor.id)

    @app.get('/api/v1/farmer/plots/{plot_id}')
    def get_plot(plot_id: UUID, actor: Actor = Depends(require_roles(Role.FARMER))) -> dict:
        result = plot_repository().get(actor.id, plot_id)
        if result is None:
            raise HTTPException(status_code=404, detail='PLOT_NOT_FOUND')
        return result

    @app.patch('/api/v1/farmer/plots/{plot_id}')
    def update_plot(plot_id: UUID, body: PlotUpdate,
                    actor: Actor = Depends(require_roles(Role.FARMER))) -> dict:
        repository = plot_repository()
        existing = repository.get(actor.id, plot_id)
        if existing is None or existing['status'] != 'active':
            raise HTTPException(status_code=404, detail='PLOT_NOT_FOUND')
        editable = set(PlotInput.model_fields)
        merged = {key: existing.get(key) for key in editable if key != 'location_permission'}
        merged['location_permission'] = existing.get('location_permission_at') is not None
        merged.update(body.model_dump(exclude_unset=True))
        # A validated complete record prevents partial updates from bypassing location consent.
        try:
            validated = PlotInput.model_validate(merged)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail='INVALID_PLOT_UPDATE') from exc
        if not repository.update(actor.id, plot_id, validated.model_dump()):
            raise HTTPException(status_code=409, detail='PLOT_UPDATE_DENIED')
        return repository.get(actor.id, plot_id)

    @app.post('/api/v1/farmer/plots/{plot_id}/archive')
    def archive_plot(plot_id: UUID, actor: Actor = Depends(require_roles(Role.FARMER))) -> dict[str, str]:
        if not plot_repository().archive(actor.id, plot_id):
            raise HTTPException(status_code=404, detail='PLOT_NOT_FOUND')
        return {'status': 'archived'}

    @app.post('/api/v1/farmer/plots/{plot_id}/select')
    def select_plot(plot_id: UUID, actor: Actor = Depends(require_roles(Role.FARMER))) -> dict[str, str]:
        if not plot_repository().select(actor.id, plot_id):
            raise HTTPException(status_code=404, detail='PLOT_NOT_FOUND')
        return {'status': 'selected'}

    @app.get('/api/v1/farmer/plots/{plot_id}/weather/context')
    def plot_weather_context(plot_id: UUID, actor: Actor = Depends(require_roles(Role.FARMER))) -> dict:
        plot = plot_repository().get(actor.id, plot_id)
        if plot is None or plot['status'] != 'active':
            raise HTTPException(status_code=404, detail='PLOT_NOT_FOUND')
        return weather.context(actor.id, plot)

    @app.get('/api/v1/{partner_role}/application/status')
    def partner_application_status(partner_role: str,actor: Actor=Depends(applicant_actor)) -> dict:
        if partner_role!=actor.role.value:
            raise HTTPException(status_code=403,detail='ROLE_FORBIDDEN')
        state=partners.state(actor.id)
        return {'application_id':state['application_id'],'status':state['status'],'role':actor.role.value}

    @app.get('/api/v1/{partner_role}/profile')
    def own_partner_profile(partner_role: str,actor: Actor=Depends(applicant_actor)) -> dict:
        if partner_role!=actor.role.value:
            raise HTTPException(status_code=403,detail='ROLE_FORBIDDEN')
        return partners.state(actor.id)

    @app.patch('/api/v1/{partner_role}/profile')
    def update_partner_profile(partner_role: str,body: PartnerProfileUpdate,actor: Actor=Depends(applicant_actor)) -> dict[str,str]:
        if partner_role!=actor.role.value:
            raise HTTPException(status_code=403,detail='ROLE_FORBIDDEN')
        if not partners.update(actor.id,body.model_dump()):
            raise HTTPException(status_code=409,detail='PROFILE_UPDATE_DENIED')
        return {'status':'updated'}

    @app.get('/api/v1/admin/partner-applications')
    def admin_partner_applications(role: str | None=None,actor: Actor=Depends(require_roles(Role.ADMIN,Role.SUPER_ADMIN))) -> list[dict]:
        if role not in (None,'shop','consultant'):
            raise HTTPException(status_code=400,detail='INVALID_ROLE')
        return partners.pending(role) if partners else []

    @app.get('/api/v1/admin/partner-applications/{application_id}')
    def admin_partner_application(application_id: UUID,actor: Actor=Depends(require_roles(Role.ADMIN,Role.SUPER_ADMIN))) -> dict:
        result=partners.detail(application_id) if partners else None
        if result is None:
            raise HTTPException(status_code=404,detail='APPLICATION_NOT_FOUND')
        return result

    @app.get('/api/v1/admin/partner-applications/{application_id}/history')
    def admin_partner_history(application_id: UUID,actor: Actor=Depends(require_roles(Role.ADMIN,Role.SUPER_ADMIN))) -> list[dict]:
        return partners.history(application_id) if partners else []

    def decide_partner(application_id: UUID,actor: Actor,action: str,body: PartnerDecision) -> dict[str,str]:
        if partners is None or not partners.decision(application_id,actor.id,action,body.reason):
            raise HTTPException(status_code=409,detail='INVALID_APPLICATION_TRANSITION')
        return {'status':'updated'}

    @app.post('/api/v1/admin/partner-applications/{application_id}/approve')
    def approve_partner(application_id: UUID,body: PartnerDecision,actor: Actor=Depends(require_recent_admin)) -> dict[str,str]:
        return decide_partner(application_id,actor,'approve',body)

    @app.post('/api/v1/admin/partner-applications/{application_id}/reject')
    def reject_partner(application_id: UUID,body: PartnerDecision,actor: Actor=Depends(require_recent_admin)) -> dict[str,str]:
        return decide_partner(application_id,actor,'reject',body)

    @app.post('/api/v1/admin/partners/{partner_id}/suspend')
    def suspend_partner(partner_id: UUID,body: PartnerDecision,actor: Actor=Depends(require_recent_admin)) -> dict[str,str]:
        application_id=partners.application_for_user(partner_id) if partners else None
        if application_id is None:
            raise HTTPException(status_code=404,detail='APPLICATION_NOT_FOUND')
        return decide_partner(application_id,actor,'suspend',body)

    @app.post('/api/v1/admin/partners/{partner_id}/reactivate')
    def reactivate_partner(partner_id: UUID,body: PartnerDecision,actor: Actor=Depends(require_recent_admin)) -> dict[str,str]:
        application_id=partners.application_for_user(partner_id) if partners else None
        if application_id is None:
            raise HTTPException(status_code=404,detail='APPLICATION_NOT_FOUND')
        return decide_partner(application_id,actor,'reactivate',body)

    @app.post('/api/v1/auth/password/reset/verify')
    def verify_password_reset(body: ResetVerify, response: Response) -> dict[str, str]:
        if not hasattr(otp, 'verify_reset'):
            raise HTTPException(status_code=503, detail='AUTH_NOT_CONFIGURED')
        secret = secrets.token_urlsafe(32)
        digest = hashlib.sha256(secret.encode('ascii')).hexdigest()
        try:
            allowed = otp.verify_reset(body.challenge_id, body.mobile_number, body.otp, digest)
        except Exception:
            raise HTTPException(status_code=401, detail='INVALID_RESET_CHALLENGE')
        if not allowed:
            raise HTTPException(status_code=401, detail='INVALID_RESET_CHALLENGE')
        response.headers['Cache-Control'] = 'no-store'
        return {'reset_token': secret}

    @app.post('/api/v1/auth/password/reset', status_code=204)
    def complete_password_reset(body: ResetComplete) -> None:
        if credentials is None:
            raise HTTPException(status_code=503, detail='AUTH_NOT_CONFIGURED')
        if body.new_password != body.confirm_password:
            raise HTTPException(status_code=400, detail='PASSWORD_CONFIRMATION_MISMATCH')
        from .passwords import validate_password
        try:
            validate_password(body.new_password)
        except ValueError:
            raise HTTPException(status_code=400, detail='WEAK_PASSWORD')
        digest = hashlib.sha256(body.reset_token.encode('ascii')).hexdigest()
        try:
            valid = credentials.complete_reset(digest, body.new_password)
        except Exception:
            raise HTTPException(status_code=503, detail='AUTH_BACKEND_UNAVAILABLE')
        if not valid:
            raise HTTPException(status_code=401, detail='INVALID_RESET_TOKEN')

    @app.post('/api/v1/auth/password/change', status_code=204)
    def change_password(body: PasswordChange, actor: Actor = Depends(session_actor)) -> None:
        allowed = actor.role == Role.FARMER and actor.state == AccountState.ACTIVE
        if actor.role in (Role.SHOP,Role.CONSULTANT) and partners:
            state = partners.state(actor.id)
            allowed = bool(state and (state['status'],actor.state) in (
                ('pending_approval',AccountState.PENDING_APPROVAL),('approved',AccountState.ACTIVE)))
        if actor.role in (Role.ADMIN,Role.SUPER_ADMIN) and admins:
            allowed = actor.state==AccountState.ACTIVE and admins.active(actor.id)
        if credentials is None or not allowed:
            raise HTTPException(status_code=403, detail='ROLE_FORBIDDEN')
        if body.new_password != body.confirm_password:
            raise HTTPException(status_code=400, detail='PASSWORD_CONFIRMATION_MISMATCH')
        from .passwords import validate_password
        try:
            validate_password(body.new_password)
        except ValueError:
            raise HTTPException(status_code=400, detail='WEAK_PASSWORD')
        try:
            changed = credentials.change_authenticated(actor.id, body.current_password, body.new_password)
        except Exception:
            raise HTTPException(status_code=503, detail='AUTH_BACKEND_UNAVAILABLE')
        if not changed:
            raise HTTPException(status_code=401, detail='INVALID_CREDENTIALS')

    @app.post('/api/v1/admin/reauth')
    def admin_reauth(body: AdminReauth,request: Request,
                     bearer_credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                     actor: Actor = Depends(require_roles(Role.ADMIN,Role.SUPER_ADMIN))) -> dict[str,str|int]:
        if tokens is None or credentials is None or bearer_credentials is None:
            raise HTTPException(status_code=503,detail='AUTH_NOT_CONFIGURED')
        try:
            from .passwords import verify_password
            if not credentials.allow_attempt(str(actor.id),request.client.host if request.client else 'unknown'):
                raise AuthenticationError('INVALID_CREDENTIALS')
            if not hasattr(credentials,'allow_admin_attempt') or not credentials.allow_admin_attempt(
                str(actor.id),request.client.host if request.client else 'unknown'):
                raise AuthenticationError('INVALID_CREDENTIALS')
            if not verify_password(body.current_password,credentials.password_hash(actor.id)):
                raise AuthenticationError('INVALID_CREDENTIALS')
            access=tokens.decode_access(bearer_credentials.credentials)
            return {'reauth_token':tokens.issue_admin_reauth(actor.id,access.session_id),'expires_in':300}
        except AuthenticationError:
            raise HTTPException(status_code=401,detail='INVALID_CREDENTIALS')
        except Exception as exc:
            raise HTTPException(status_code=503,detail='AUTH_BACKEND_UNAVAILABLE') from exc

    @app.post("/api/v1/auth/otp/verify")
    def verify_otp(body: OtpVerification, response: Response) -> dict[str, str | int]:
        if workflow is None:
            raise HTTPException(status_code=503, detail="AUTH_NOT_CONFIGURED")
        try:
            pair = workflow.verify_otp(body.mobile, body.code)
        except AuthenticationError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail="AUTH_BACKEND_UNAVAILABLE") from exc
        response.headers["Cache-Control"] = "no-store"
        return pair

    @app.post("/api/v1/auth/refresh")
    def refresh(body: RefreshRequest, response: Response) -> dict[str, str | int]:
        if workflow is None:
            raise HTTPException(status_code=503, detail="AUTH_NOT_CONFIGURED")
        try:
            pair = workflow.refresh(body.refresh_token)
            issued = tokens.decode_access(pair['access_token'])
            refreshed_actor = store.get_actor(issued.user_id)
            if refreshed_actor and refreshed_actor.role in (Role.ADMIN,Role.SUPER_ADMIN):
                if admins is None or not admins.active(refreshed_actor.id):
                    sessions.revoke(issued.session_id)
                    raise AuthenticationError('ACCOUNT_NOT_ACTIVE')
        except AuthenticationError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail="AUTH_BACKEND_UNAVAILABLE") from exc
        response.headers["Cache-Control"] = "no-store"
        return pair

    @app.post("/api/v1/auth/logout", status_code=204)
    def logout(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), actor: Actor = Depends(session_actor)) -> None:
        assert tokens is not None and credentials is not None
        identity = tokens.decode_access(credentials.credentials)
        try:
            sessions.revoke(identity.session_id)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="AUTH_BACKEND_UNAVAILABLE") from exc

    @app.get("/api/v1/admin/overview")
    def admin_overview(
        actor: Actor = Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    ) -> dict[str, str]:
        return {"role": actor.role.value, "status": "shell"}

    @app.post("/api/v1/admin/farmers/pre-register", status_code=201)
    def prepare_farmer(body: FarmerPreparation, actor: Actor = Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))) -> dict[str, str]:
        try:
            farmer_id = store.prepare_farmer(body.mobile, actor.id, body.reason)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="IDENTITY_UNAVAILABLE") from exc
        return {"farmer_id": str(farmer_id), "status": "pending_or_existing"}

    @app.get("/api/v1/partner/overview")
    def partner_overview(
        actor: Actor = Depends(require_roles(Role.SHOP, Role.CONSULTANT)),
    ) -> dict[str, str]:
        return {"role": actor.role.value, "status": "shell"}

    @app.get("/api/v1/farmer/overview")
    def farmer_overview(
        actor: Actor = Depends(require_roles(Role.FARMER)),
    ) -> dict[str, str]:
        return {"role": actor.role.value, "status": "shell"}

    return app


app = create_app()
