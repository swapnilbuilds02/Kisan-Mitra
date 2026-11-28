"""Narrow PostgreSQL adapter for Farmer onboarding and self-profile access."""

from uuid import UUID

from .identity import PostgresIdentityStore
from .passwords import hash_password


class PostgresFarmerOnboarding:
    def __init__(self, identity: PostgresIdentityStore) -> None:
        self.identity = identity

    def target(self, mobile: str) -> tuple[UUID | None, str] | None:
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT subject,otp_purpose FROM km_private.farmer_onboarding_target(%s)', (mobile,))
                return cursor.fetchone()

    def complete(self, token_digest: str, password: str, profile: dict) -> UUID | None:
        encoded = hash_password(password)
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.complete_farmer_onboarding(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                    (token_digest, encoded, profile['full_name'], profile['preferred_language'],
                     profile['village'], profile['taluka'], profile['district'], profile['state'],
                     profile.get('pincode') or '', profile['consent_document_id'], profile['consent_version']))
                return cursor.fetchone()[0]

    def profile(self, user_id: UUID) -> dict | None:
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT * FROM km_private.farmer_profile_for(%s)', (user_id,))
                row = cursor.fetchone()
                if row is None:
                    return None
                return dict(zip(('full_name','preferred_language','village','taluka','district','state','pincode','profile_completed_at'), row))

    def update(self, user_id: UUID, profile: dict) -> bool:
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.update_farmer_profile(%s,%s,%s,%s,%s,%s,%s,%s)',
                    (user_id,profile['full_name'],profile['preferred_language'],profile['village'],
                     profile['taluka'],profile['district'],profile['state'],profile.get('pincode') or ''))
                return bool(cursor.fetchone()[0])
