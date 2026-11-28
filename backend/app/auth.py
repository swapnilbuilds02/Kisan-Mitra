"""Phase 1 token and OTP contracts. No live OTP or session adapter is enabled."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal, Protocol
from uuid import UUID, uuid4

import jwt
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from .identity import AccountState, Actor, IdentityStore, Role
from .identity import normalize_mobile
from .passwords import verify_password

ISSUER = "https://api.kisanmitra.in"
AUDIENCE = "kisan-mitra-clients"
ACCESS_TTL_SECONDS = 900
REFRESH_TTL_SECONDS = 30 * 24 * 60 * 60
ADMIN_REAUTH_TTL_SECONDS = 300


class AuthenticationError(Exception):
    pass


class OtpProvider(Protocol):
    """Provider must enforce request rate limits and one-use 120-second OTPs."""

    def request(self, mobile: str, client_ip: str) -> None: ...
    def verify(self, mobile: str, code: str) -> bool: ...
    def ready(self) -> bool: ...


class SessionStore(Protocol):
    """Rotate atomically; a reused hash revokes all user sessions in that operation."""

    def create(self, user_id: UUID, refresh_hash: str, ttl_seconds: int) -> UUID: ...
    def active(self, user_id: UUID, session_id: UUID) -> bool: ...
    def rotate(self, session_id: UUID, old_hash: str, new_hash: str, ttl_seconds: int) -> tuple[Literal["rotated", "reused", "invalid"], UUID | None]: ...
    def revoke(self, session_id: UUID) -> None: ...
    def revoke_user(self, user_id: UUID) -> None: ...
    def ready(self) -> bool: ...


class UnavailableOtpProvider:
    def request(self, mobile: str, client_ip: str) -> None:
        raise RuntimeError("OTP provider is not configured")

    def verify(self, mobile: str, code: str) -> bool:
        raise RuntimeError("OTP provider is not configured")

    def ready(self) -> bool:
        return False


class UnavailableSessionStore:
    def create(self, user_id: UUID, refresh_hash: str, ttl_seconds: int) -> UUID:
        raise RuntimeError("Session store is not configured")

    def active(self, user_id: UUID, session_id: UUID) -> bool:
        raise RuntimeError("Session store is not configured")

    def rotate(self, session_id: UUID, old_hash: str, new_hash: str, ttl_seconds: int) -> tuple[Literal["rotated", "reused", "invalid"], UUID | None]:
        raise RuntimeError("Session store is not configured")

    def revoke(self, session_id: UUID) -> None:
        raise RuntimeError("Session store is not configured")

    def revoke_user(self, user_id: UUID) -> None:
        raise RuntimeError("Session store is not configured")

    def ready(self) -> bool:
        return False


@dataclass(frozen=True)
class AccessIdentity:
    user_id: UUID
    session_id: UUID


class TokenService:
    def __init__(self, private_key_pem: str, public_keys: dict[str, str], active_kid: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", active_kid) or active_kid not in public_keys:
            raise ValueError("An active signing key ID is required")
        try:
            private = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
            parsed = {
                kid: serialization.load_pem_public_key(pem.encode("utf-8"))
                for kid, pem in public_keys.items()
                if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", kid)
            }
        except (TypeError, ValueError, UnsupportedAlgorithm) as exc:
            raise ValueError("Invalid RSA key configuration") from exc
        if not isinstance(private, rsa.RSAPrivateKey) or private.key_size < 2048:
            raise ValueError("An RSA private key of at least 2048 bits is required")
        if len(parsed) != len(public_keys) or any(not isinstance(key, rsa.RSAPublicKey) or key.key_size < 2048 for key in parsed.values()):
            raise ValueError("Invalid RSA public key ring")
        if private.public_key().public_numbers() != parsed[active_kid].public_numbers():
            raise ValueError("Active private/public key mismatch")
        self._private = private
        self._public = parsed
        self._active_kid = active_kid

    @classmethod
    def from_environment(cls) -> "TokenService | None":
        import os
        private = os.getenv("JWT_PRIVATE_KEY_PEM", "")
        public_json = os.getenv("JWT_PUBLIC_KEYS_JSON", "")
        kid = os.getenv("JWT_ACTIVE_KID", "")
        if not private or not public_json or not kid:
            return None
        try:
            keys = json.loads(public_json)
            if not isinstance(keys, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in keys.items()):
                return None
            return cls(private, keys, kid)
        except (ValueError, TypeError):
            return None

    def issue_access(self, user_id: UUID, session_id: UUID) -> str:
        now = datetime.now(timezone.utc)
        return jwt.encode(
            {
                "sub": str(user_id), "sid": str(session_id), "jti": str(uuid4()),
                "typ": "access", "iat": now, "nbf": now,
                "exp": now + timedelta(seconds=ACCESS_TTL_SECONDS),
                "iss": ISSUER, "aud": AUDIENCE,
            },
            self._private,
            algorithm="RS256",
            headers={"kid": self._active_kid, "typ": "JWT"},
        )

    def decode_access(self, token: str) -> AccessIdentity:
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
                raise AuthenticationError("INVALID_TOKEN")
            key = self._public.get(header["kid"])
            if key is None:
                raise AuthenticationError("INVALID_TOKEN")
            claims = jwt.decode(
                token, key, algorithms=["RS256"],
                issuer=ISSUER, audience=AUDIENCE,
                options={"require": ["sub", "sid", "jti", "typ", "iat", "nbf", "exp", "iss", "aud"]},
                leeway=0,
            )
            if claims["typ"] != "access":
                raise AuthenticationError("INVALID_TOKEN")
            return AccessIdentity(UUID(claims["sub"]), UUID(claims["sid"]))
        except (jwt.InvalidTokenError, ValueError, KeyError, TypeError) as exc:
            raise AuthenticationError("INVALID_TOKEN") from exc

    def issue_admin_reauth(self, user_id: UUID, session_id: UUID) -> str:
        now = datetime.now(timezone.utc)
        return jwt.encode({"sub":str(user_id),"sid":str(session_id),"jti":str(uuid4()),
                           "typ":"admin_reauth","iat":now,"nbf":now,
                           "exp":now+timedelta(seconds=ADMIN_REAUTH_TTL_SECONDS),
                           "iss":ISSUER,"aud":AUDIENCE},self._private,algorithm="RS256",
                          headers={"kid":self._active_kid,"typ":"JWT"})

    def decode_admin_reauth(self, token: str) -> AccessIdentity:
        try:
            header=jwt.get_unverified_header(token)
            if header.get('alg')!='RS256' or not isinstance(header.get('kid'),str):
                raise AuthenticationError('INVALID_REAUTH')
            key=self._public.get(header['kid'])
            if key is None:
                raise AuthenticationError('INVALID_REAUTH')
            claims=jwt.decode(token,key,algorithms=['RS256'],issuer=ISSUER,audience=AUDIENCE,
                              options={'require':['sub','sid','jti','typ','iat','nbf','exp','iss','aud']},leeway=0)
            if claims['typ']!='admin_reauth':
                raise AuthenticationError('INVALID_REAUTH')
            return AccessIdentity(UUID(claims['sub']),UUID(claims['sid']))
        except (jwt.InvalidTokenError,ValueError,KeyError,TypeError) as exc:
            raise AuthenticationError('INVALID_REAUTH') from exc


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _refresh_session_id(value: str) -> UUID:
    try:
        session, random_part = value.split(".", 1)
        if len(value) > 256 or not re.fullmatch(r"[A-Za-z0-9_-]{43}", random_part):
            raise ValueError("Malformed refresh token")
        return UUID(session)
    except (ValueError, AttributeError) as exc:
        raise AuthenticationError("INVALID_REFRESH_TOKEN") from exc


class AuthWorkflow:
    def __init__(self, identity: IdentityStore, otp: OtpProvider, sessions: SessionStore, tokens: TokenService) -> None:
        self.identity = identity
        self.otp = otp
        self.sessions = sessions
        self.tokens = tokens

    def request_otp(self, mobile: str, client_ip: str) -> None:
        self.otp.request(mobile, client_ip)

    def verify_otp(self, mobile: str, code: str) -> dict[str, str | int]:
        if not self.otp.verify(mobile, code):
            raise AuthenticationError("INVALID_OTP")
        actor = self.identity.get_actor_by_mobile(mobile)
        # The legacy LOGIN route is for already verified active Farmers only.
        # Registration and pending account claims require the onboarding flow.
        if actor is None or actor.state != AccountState.ACTIVE or actor.role != Role.FARMER:
            raise AuthenticationError("INVALID_OTP")
        initial_secret = secrets.token_urlsafe(32)
        session_id = self.sessions.create(actor.id, _digest(initial_secret), REFRESH_TTL_SECONDS)
        refresh = f"{session_id}.{initial_secret}"
        return self._pair(actor, session_id, refresh)

    def login_password(self, mobile: str, password: str, client_ip: str, credentials) -> dict[str, str | int]:
        mobile = normalize_mobile(mobile)
        if not credentials.allow_attempt(mobile, client_ip):
            raise AuthenticationError('INVALID_CREDENTIALS')
        actor = credentials.find_actor(mobile)
        if actor and actor.role in (Role.ADMIN, Role.SUPER_ADMIN):
            if not hasattr(credentials, 'allow_admin_attempt') or not credentials.allow_admin_attempt(mobile, client_ip):
                raise AuthenticationError('INVALID_CREDENTIALS')
        encoded = credentials.password_hash(actor.id) if actor else None
        # Compute a real scrypt digest even for unknown accounts to narrow timing differences.
        if not verify_password(password, encoded):
            raise AuthenticationError('INVALID_CREDENTIALS')
        if actor is None or actor.state not in (AccountState.ACTIVE, AccountState.PENDING_APPROVAL):
            raise AuthenticationError('INVALID_CREDENTIALS')
        # Database session creation repeats these checks under an identity row lock.
        if actor.role == Role.FARMER and actor.state != AccountState.ACTIVE:
            raise AuthenticationError('INVALID_CREDENTIALS')
        if actor.role in (Role.SHOP, Role.CONSULTANT):
            status = credentials.partner_status(actor.id) if hasattr(credentials, 'partner_status') else None
            if (status, actor.state) not in (('pending_approval', AccountState.PENDING_APPROVAL),
                                             ('approved', AccountState.ACTIVE)):
                raise AuthenticationError('INVALID_CREDENTIALS')
        elif actor.role in (Role.ADMIN, Role.SUPER_ADMIN):
            if actor.state != AccountState.ACTIVE or not (
                hasattr(credentials, 'admin_active') and credentials.admin_active(actor.id)
            ):
                raise AuthenticationError('INVALID_CREDENTIALS')
        elif actor.role != Role.FARMER:
            raise AuthenticationError('INVALID_CREDENTIALS')
        initial_secret = secrets.token_urlsafe(32)
        if not hasattr(self.sessions, 'create_password'):
            raise AuthenticationError('INVALID_CREDENTIALS')
        session_id = self.sessions.create_password(actor.id, _digest(initial_secret), REFRESH_TTL_SECONDS, encoded)
        if session_id is None:
            raise AuthenticationError('INVALID_CREDENTIALS')
        return self._pair(actor, session_id, f'{session_id}.{initial_secret}')

    def refresh(self, refresh_token: str) -> dict[str, str | int]:
        session_id = _refresh_session_id(refresh_token)
        new_secret = secrets.token_urlsafe(32)
        new_refresh = f"{session_id}.{new_secret}"
        result, user_id = self.sessions.rotate(session_id, _digest(refresh_token.split(".", 1)[1]), _digest(new_secret), REFRESH_TTL_SECONDS)
        if result != "rotated" or user_id is None:
            raise AuthenticationError("INVALID_REFRESH_TOKEN")
        actor = self.identity.get_actor(user_id)
        if actor is None or actor.state not in (AccountState.ACTIVE, AccountState.PENDING_APPROVAL):
            self.sessions.revoke(session_id)
            raise AuthenticationError("ACCOUNT_NOT_ACTIVE")
        if actor.state == AccountState.PENDING_APPROVAL and actor.role not in (Role.SHOP, Role.CONSULTANT):
            self.sessions.revoke(session_id)
            raise AuthenticationError("ACCOUNT_NOT_ACTIVE")
        return self._pair(actor, session_id, new_refresh)

    def _pair(self, actor: Actor, session_id: UUID, refresh: str) -> dict[str, str | int]:
        return {
            "access_token": self.tokens.issue_access(actor.id, session_id),
            "refresh_token": refresh,
            "token_type": "bearer",
            "expires_in": ACCESS_TTL_SECONDS,
        }
