"""PostgreSQL auth state adapters; SQL functions own atomic transitions.

No SMS sender is bundled or selected by environment variables. A caller must
explicitly inject a delivery adapter before OTPs can leave the server.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Protocol
from uuid import UUID


def _connect(database_url: str):
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("psycopg is required for PostgreSQL auth state") from exc
    return psycopg.connect(database_url, connect_timeout=3)


def _ready(database_url: str) -> bool:
    try:
        with _connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone() == (1,)
    except Exception:
        return False


class PostgresSessionStore:
    def __init__(self, database_url: str) -> None:
        if not database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("A PostgreSQL DATABASE_URL is required")
        self.database_url = database_url

    def create(self, user_id: UUID, refresh_hash: str, ttl_seconds: int) -> UUID:
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT km_private.create_session(%s,%s,%s)", (user_id, refresh_hash, ttl_seconds))
                return cursor.fetchone()[0]

    def create_password(self, user_id: UUID, refresh_hash: str, ttl_seconds: int, credential_hash: str) -> UUID | None:
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.create_password_session(%s,%s,%s,%s)',
                    (user_id, refresh_hash, ttl_seconds, credential_hash))
                return cursor.fetchone()[0]

    def create_partner(self, user_id: UUID, refresh_hash: str, ttl_seconds: int) -> UUID | None:
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.create_partner_session(%s,%s,%s)', (user_id,refresh_hash,ttl_seconds))
                return cursor.fetchone()[0]

    def create_admin(self, user_id: UUID, refresh_hash: str, ttl_seconds: int) -> UUID | None:
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.create_admin_session(%s,%s,%s)', (user_id, refresh_hash, ttl_seconds))
                return cursor.fetchone()[0]

    def active(self, user_id: UUID, session_id: UUID) -> bool:
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT km_private.session_active(%s,%s)", (user_id, session_id))
                return bool(cursor.fetchone()[0])

    def rotate(self, session_id: UUID, old_hash: str, new_hash: str, ttl_seconds: int) -> tuple[str, UUID | None]:
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT result, subject FROM km_private.rotate_session(%s,%s,%s,%s)", (session_id, old_hash, new_hash, ttl_seconds))
                return cursor.fetchone()

    def revoke(self, session_id: UUID) -> None:
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT km_private.revoke_session(%s)", (session_id,))

    def revoke_user(self, user_id: UUID) -> None:
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT km_private.revoke_user_sessions(%s)", (user_id,))

    def ready(self) -> bool:
        return _ready(self.database_url)


class OtpSender(Protocol):
    def send(self, mobile: str, code: str) -> None: ...
    def ready(self) -> bool: ...


class PostgresOtpProvider:
    def __init__(self, database_url: str, pepper: str, sender: OtpSender) -> None:
        if not database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("A PostgreSQL DATABASE_URL is required")
        if len(pepper.encode("utf-8")) < 32:
            raise ValueError("OTP_PEPPER must be at least 32 bytes")
        self.database_url = database_url
        self._pepper = pepper.encode("utf-8")
        self.sender = sender

    def _hash(self, purpose: str, value: str) -> str:
        return hmac.new(self._pepper, f"{purpose}:{value}".encode("utf-8"), hashlib.sha256).hexdigest()

    def request(self, mobile: str, client_ip: str) -> None:
        code = f"{secrets.randbelow(1_000_000):06d}"
        mobile_hash = self._hash("mobile", mobile)
        ip_hash = self._hash("ip", client_ip)
        code_hash = self._hash("otp", f"{mobile}:{code}")
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT km_private.issue_otp(%s,%s,%s,%s)", (mobile, mobile_hash, ip_hash, code_hash))
                allowed = cursor.fetchone()[0]
        if allowed:
            self.sender.send(mobile, code)

    def verify(self, mobile: str, code: str) -> bool:
        mobile_hash = self._hash("mobile", mobile)
        code_hash = self._hash("otp", f"{mobile}:{code}")
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT km_private.consume_otp(%s,%s,%s)", (mobile, mobile_hash, code_hash))
                return bool(cursor.fetchone()[0])

    def ready(self) -> bool:
        return self.sender.ready() and _ready(self.database_url)

    def request_purpose(self, mobile: str, client_ip: str, purpose: str, subject: UUID | None) -> UUID | None:
        if purpose not in ('REGISTRATION', 'LOGIN', 'ACCOUNT_CLAIM', 'PASSWORD_RESET'):
            raise ValueError('Invalid OTP purpose')
        code = f'{secrets.randbelow(1_000_000):06d}'
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.issue_purpose_otp(%s,%s,%s,%s,%s,%s)',
                    (mobile, self._hash('mobile', mobile), self._hash('ip', client_ip),
                     self._hash('otp', f'{"ONBOARDING" if purpose in ("REGISTRATION", "ACCOUNT_CLAIM") else purpose}:{mobile}:{code}'), purpose, subject))
                challenge_id = cursor.fetchone()[0]
        if challenge_id:
            self.sender.send(mobile, code)
        return challenge_id

    def verify_reset(self, challenge_id: UUID, mobile: str, code: str, token_digest: str) -> bool:
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.consume_reset_otp(%s,%s,%s)',
                    (challenge_id, self._hash('otp', f'PASSWORD_RESET:{mobile}:{code}'), token_digest))
                return cursor.fetchone()[0] is not None

    def verify_onboarding(self, challenge_id: UUID, mobile: str, code: str, token_digest: str) -> bool:
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.consume_onboarding_otp(%s,%s,%s)',
                    (challenge_id, self._hash('otp', f'ONBOARDING:{mobile}:{code}'), token_digest))
                return bool(cursor.fetchone()[0])

    def request_partner(self, mobile: str, client_ip: str, role: str) -> UUID | None:
        if role not in ('shop','consultant'):
            raise ValueError('Invalid partner role')
        code = f'{secrets.randbelow(1_000_000):06d}'
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.issue_partner_otp(%s,%s,%s,%s,%s)',
                    (mobile,self._hash('mobile',mobile),self._hash('ip',client_ip),
                     self._hash('otp',f'ONBOARDING:{mobile}:{code}'),role))
                challenge = cursor.fetchone()[0]
        if challenge:
            self.sender.send(mobile,code)
        return challenge

    def verify_partner(self, challenge: UUID, mobile: str, code: str, token_digest: str, role: str) -> bool:
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.consume_partner_registration_otp(%s,%s,%s,%s)',
                    (challenge,self._hash('otp',f'ONBOARDING:{mobile}:{code}'),token_digest,role))
                return bool(cursor.fetchone()[0])

    def verify_partner_login(self, challenge: UUID, mobile: str, subject: UUID, code: str) -> bool:
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.consume_partner_login_otp(%s,%s,%s,%s)',
                    (challenge,mobile,subject,self._hash('otp',f'LOGIN:{mobile}:{code}')))
                return bool(cursor.fetchone()[0])

    def request_partner_reset(self, mobile: str, client_ip: str, subject: UUID | None) -> UUID | None:
        code=f'{secrets.randbelow(1_000_000):06d}'
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.issue_partner_reset_otp(%s,%s,%s,%s,%s)',
                    (mobile,self._hash('mobile',mobile),self._hash('ip',client_ip),
                     self._hash('otp',f'PASSWORD_RESET:{mobile}:{code}'),subject))
                challenge=cursor.fetchone()[0]
        if challenge:
            self.sender.send(mobile,code)
        return challenge

    def verify_admin_onboarding(self, challenge: UUID, mobile: str, code: str, token_digest: str) -> bool:
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.consume_admin_verification_otp(%s,%s,%s,%s)',
                    (challenge,mobile,self._hash('otp',f'ONBOARDING:{mobile}:{code}'),token_digest))
                return bool(cursor.fetchone()[0])

    def verify_admin_login(self, challenge: UUID, mobile: str, subject: UUID, code: str) -> bool:
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.consume_admin_login_otp(%s,%s,%s,%s)',
                    (challenge,mobile,subject,self._hash('otp',f'LOGIN:{mobile}:{code}')))
                return bool(cursor.fetchone()[0])

    def request_admin_reset(self, mobile: str, client_ip: str, subject: UUID | None) -> UUID | None:
        code=f'{secrets.randbelow(1_000_000):06d}'
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.issue_admin_reset_otp(%s,%s,%s,%s,%s)',
                    (mobile,self._hash('mobile',mobile),self._hash('ip',client_ip),
                     self._hash('otp',f'PASSWORD_RESET:{mobile}:{code}'),subject))
                challenge=cursor.fetchone()[0]
        if challenge:
            self.sender.send(mobile,code)
        return challenge

    def allow_admin_attempt(self, mobile: str, client_ip: str) -> bool:
        with _connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.admin_auth_attempt(%s,%s,%s)',
                    (self._hash('admin-mobile',mobile),self._hash('admin-ip',client_ip),'otp'))
                return bool(cursor.fetchone()[0])
