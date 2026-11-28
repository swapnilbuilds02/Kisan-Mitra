"""Identity lookup and role state for the first API shell.

Tokens carry only a subject. Roles and account state come from the server-side
store on every request, so changing a user's role or suspension takes effect
without waiting for a token to expire.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re
from typing import Protocol
from uuid import UUID


def normalize_mobile(value: str) -> str:
    """Canonical India mobile storage: ten ASCII digits, country code separate."""
    match = re.fullmatch(r"(?:\+91|91)?([6-9][0-9]{9})", value.strip())
    if match is None:
        raise ValueError("A valid Indian mobile number is required")
    return match.group(1)


class Role(StrEnum):
    FARMER = "farmer"
    SHOP = "shop"
    CONSULTANT = "consultant"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class AccountState(StrEnum):
    ACTIVE = "active"
    PENDING_APPROVAL = "pending_approval"
    SUSPENDED = "suspended"
    EXPIRED = "expired"


@dataclass(frozen=True)
class Actor:
    id: UUID
    role: Role
    state: AccountState
    account_tier: str = "free"


class IdentityStore(Protocol):
    def get_actor(self, user_id: UUID) -> Actor | None: ...
    def get_actor_by_mobile(self, mobile: str) -> Actor | None: ...
    def claim_farmer(self, mobile: str) -> Actor | None: ...
    def prepare_farmer(self, mobile: str, operator_id: UUID, reason: str) -> UUID: ...
    def ready(self) -> bool: ...


class UnavailableIdentityStore:
    """Fail closed until a real database store is configured."""

    def get_actor(self, user_id: UUID) -> Actor | None:
        raise RuntimeError("Identity database is not configured")

    def get_actor_by_mobile(self, mobile: str) -> Actor | None:
        raise RuntimeError("Identity database is not configured")

    def claim_farmer(self, mobile: str) -> Actor | None:
        raise RuntimeError("Identity database is not configured")

    def prepare_farmer(self, mobile: str, operator_id: UUID, reason: str) -> UUID:
        raise RuntimeError("Identity database is not configured")

    def ready(self) -> bool:
        return False


class PostgresIdentityStore:
    """Read identity and partner authorization from PostgreSQL.

    This is intentionally read-only. OTP/session issuance and partner approval
    are separate Phase 1/2 workflows; no development users are seeded here.
    """

    def __init__(self, database_url: str) -> None:
        if not database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("A PostgreSQL DATABASE_URL is required")
        self._database_url = database_url

    def _connect(self):
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("Install backend/requirements.txt for PostgreSQL access") from exc
        return psycopg.connect(self._database_url, connect_timeout=3)

    def get_actor(self, user_id: UUID) -> Actor | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, role, account_state, account_tier
                    FROM km_private.lookup_actor(%s)
                    """,
                    (user_id,),
                )
                row = cursor.fetchone()
        return self._actor_from_row(row)

    def get_actor_by_mobile(self, mobile: str) -> Actor | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, role, account_state, account_tier FROM km_private.lookup_actor_by_mobile(%s)",
                    (mobile,),
                )
                row = cursor.fetchone()
        return self._actor_from_row(row)

    def claim_farmer(self, mobile: str) -> Actor | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, role, account_state, account_tier FROM km_private.claim_farmer(%s)", (mobile,))
                row = cursor.fetchone()
        return self._actor_from_row(row)

    def prepare_farmer(self, mobile: str, operator_id: UUID, reason: str) -> UUID:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT km_private.prepare_farmer(%s,%s,%s)", (mobile, operator_id, reason))
                return cursor.fetchone()[0]

    @staticmethod
    def _actor_from_row(row) -> Actor | None:
        if row is None:
            return None
        return Actor(
            id=row[0],
            role=Role(row[1]),
            state=AccountState(row[2]),
            account_tier=row[3],
        )

    def ready(self) -> bool:
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return cursor.fetchone() == (1,)
        except Exception:
            return False
