"""One password repository for every role; no public mutation route."""

import hashlib
from uuid import UUID

from .identity import Actor, PostgresIdentityStore, normalize_mobile
from .passwords import hash_password


class PostgresCredentialStore:
    def __init__(self, identity: PostgresIdentityStore, pepper: str) -> None:
        if len(pepper.encode('utf-8')) < 32:
            raise ValueError('PASSWORD_RATE_PEPPER must be at least 32 bytes')
        self.identity = identity
        self.pepper = pepper

    def find_actor(self, mobile: str) -> Actor | None:
        return self.identity.get_actor_by_mobile(normalize_mobile(mobile))

    def password_hash(self, subject: UUID) -> str | None:
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.read_password_credential(%s)', (subject,))
                return cursor.fetchone()[0]

    def partner_status(self, subject: UUID) -> str | None:
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT status FROM km_private.partner_state(%s)', (subject,))
                row = cursor.fetchone()
                return row[0] if row else None

    def admin_active(self, subject: UUID) -> bool:
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.admin_active(%s)', (subject,))
                return bool(cursor.fetchone()[0])

    def allow_attempt(self, mobile: str, ip: str) -> bool:
        mobile_digest = hashlib.sha256((self.pepper + ':m:' + mobile).encode()).hexdigest()
        ip_digest = hashlib.sha256((self.pepper + ':i:' + ip).encode()).hexdigest()
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.password_login_attempt(%s,%s)', (mobile_digest, ip_digest))
                return bool(cursor.fetchone()[0])

    def allow_admin_attempt(self, mobile: str, ip: str) -> bool:
        mobile_digest = hashlib.sha256((self.pepper + ':admin:m:' + mobile).encode()).hexdigest()
        ip_digest = hashlib.sha256((self.pepper + ':admin:i:' + ip).encode()).hexdigest()
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.admin_auth_attempt(%s,%s,%s)',
                               (mobile_digest, ip_digest, 'password'))
                return bool(cursor.fetchone()[0])

    def create_internal(self, subject: UUID, password: str) -> bool:
        encoded = hash_password(password)
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.set_password_credential(%s,%s,FALSE)', (subject, encoded))
                return bool(cursor.fetchone()[0])

    def replace_internal(self, subject: UUID, password: str) -> bool:
        encoded = hash_password(password)
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.set_password_credential(%s,%s,TRUE)', (subject, encoded))
                return bool(cursor.fetchone()[0])

    def complete_reset(self, token_digest: str, password: str) -> bool:
        encoded = hash_password(password)
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.complete_password_reset(%s,%s)', (token_digest, encoded))
                return bool(cursor.fetchone()[0])

    def change_authenticated(self, subject: UUID, current_password: str, new_password: str) -> bool:
        from .passwords import verify_password
        old_hash = self.password_hash(subject)
        if not verify_password(current_password, old_hash) or old_hash is None:
            return False
        encoded = hash_password(new_password)
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.change_password_credential(%s,%s,%s)',
                    (subject, old_hash, encoded))
                return bool(cursor.fetchone()[0])
