"""Shared Shop/Consultant application repository; SQL owns state transitions."""

from uuid import UUID

from .identity import PostgresIdentityStore
from .passwords import hash_password


class PostgresPartnerStore:
    def __init__(self, identity: PostgresIdentityStore) -> None:
        self.identity = identity

    def eligible(self, mobile: str) -> bool:
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.partner_registration_eligible(%s)', (mobile,))
                return bool(cursor.fetchone()[0])

    def complete(self, token_digest: str, password: str, role: str, profile: dict) -> UUID | None:
        encoded = hash_password(password)
        values = (token_digest,encoded,role,profile['display_name'],profile.get('representative_name') or '',
            profile.get('specialization') or '',profile.get('organization_name') or '',
            profile['preferred_language'],profile['state'],profile['district'],profile['taluka'],
            profile['locality'],profile.get('address') or '',profile.get('pincode') or '',
            profile['consent_document_id'],profile['consent_version'])
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.complete_partner_application('+','.join(['%s']*16)+')', values)
                return cursor.fetchone()[0]

    def state(self, user_id: UUID) -> dict | None:
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT * FROM km_private.partner_state(%s)', (user_id,))
                row = cursor.fetchone()
        if row is None:
            return None
        return dict(zip(('application_id','partner_role','status','display_name','preferred_language',
            'state','district','taluka','locality','address','pincode'),row))

    def pending(self, role: str | None) -> list[dict]:
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT * FROM km_private.pending_partner_applications(%s)', (role,))
                rows = cursor.fetchall()
        return [dict(zip(('application_id','user_id','partner_role','status','display_name','submitted_at'),row)) for row in rows]

    def detail(self, application_id: UUID) -> dict | None:
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT * FROM km_private.partner_application_detail(%s)', (application_id,))
                row = cursor.fetchone()
        if row is None:
            return None
        return dict(zip(('application_id','user_id','partner_role','status','display_name',
            'representative_name','specialization','organization_name','preferred_language',
            'state','district','taluka','locality','address','pincode','submitted_at'),row))

    def application_for_user(self, user_id: UUID) -> UUID | None:
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.partner_application_for_user(%s)', (user_id,))
                return cursor.fetchone()[0]

    def history(self, application_id: UUID) -> list[dict]:
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT * FROM km_private.partner_decision_history(%s)', (application_id,))
                rows = cursor.fetchall()
        return [dict(zip(('prior_status','new_status','reason','actor_id','decided_at'),row)) for row in rows]

    def update(self, user_id: UUID, profile: dict) -> bool:
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.update_partner_location('+','.join(['%s']*8)+')',
                    (user_id,profile['preferred_language'],profile['state'],profile['district'],
                     profile['taluka'],profile['locality'],profile.get('address') or '',profile.get('pincode') or ''))
                return bool(cursor.fetchone()[0])

    def decision(self, application_id: UUID, operator_id: UUID, action: str, reason: str) -> bool:
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.partner_decision(%s,%s,%s,%s)',
                    (application_id,operator_id,action,reason))
                return bool(cursor.fetchone()[0])
