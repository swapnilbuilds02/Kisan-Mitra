"""Restricted administrative provisioning over the existing identity store."""

from __future__ import annotations

import argparse
import os
from uuid import UUID

from .identity import PostgresIdentityStore, normalize_mobile
from .passwords import hash_password


class PostgresAdminProvisioning:
    def __init__(self, identity: PostgresIdentityStore) -> None:
        self.identity = identity

    def candidate(self, mobile: str) -> UUID | None:
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.admin_provisioning_candidate(%s)', (normalize_mobile(mobile),))
                return cursor.fetchone()[0]

    def active(self, subject: UUID) -> bool:
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.admin_active(%s)', (subject,))
                return bool(cursor.fetchone()[0])

    def activate(self, authorization_digest: str, password: str) -> bool:
        encoded = hash_password(password)
        with self.identity._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT km_private.activate_admin(%s,%s)', (authorization_digest, encoded))
                return bool(cursor.fetchone()[0])


def main() -> None:
    """Prepare an inactive identity; OTP verification and activation stay separate."""
    parser = argparse.ArgumentParser(description='Prepare an inactive Admin identity as migration owner')
    parser.add_argument('--mobile', required=True)
    parser.add_argument('--display-name', required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--bootstrap-owner', action='store_true')
    mode.add_argument('--operator-id', type=UUID)
    args = parser.parse_args()
    database_url = os.getenv('ADMIN_PROVISION_DATABASE_URL', '')
    if not database_url.startswith(('postgresql://', 'postgres://')):
        parser.error('ADMIN_PROVISION_DATABASE_URL must be a migration-owner PostgreSQL connection')
    import psycopg
    with psycopg.connect(database_url, connect_timeout=3) as connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT km_private.prepare_admin(%s,%s,%s,%s)',
                           (normalize_mobile(args.mobile), args.display_name, args.operator_id, args.bootstrap_owner))
            subject = cursor.fetchone()[0]
    if subject is None:
        parser.error('Provisioning denied: duplicate mobile or unauthorized bootstrap/operator')
    print(f'Prepared inactive Admin identity {subject}. Complete OTP verification and activation separately.')


if __name__ == '__main__':
    main()
