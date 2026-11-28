"""Disposable PostgreSQL checks. Set KM_TEST_DATABASE_URL to localhost/km_test_*.

The test applies and rolls back the migration. It never runs against a database
whose name does not begin with km_test_ or whose host is not local.
"""

from pathlib import Path
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")
from backend.tests.postgres_test_guard import require_disposable_database


def test_identity_migration_and_restricted_role():
    dsn = require_disposable_database(psycopg)

    migration_dir = Path(__file__).resolve().parents[1] / "migrations"
    up = (migration_dir / "0001_identity_foundation.up.sql").read_text(encoding="utf-8")
    down = (migration_dir / "0001_identity_foundation.down.sql").read_text(encoding="utf-8")
    user_a, user_b = uuid4(), uuid4()
    with psycopg.connect(dsn, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.users')")
            assert cursor.fetchone()[0] is None, "Test database must be empty of identity tables"
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = 'km_api'")
            assert cursor.fetchone() is None, "Test server must not already have km_api"
            cursor.execute(up)
            try:
                cursor.execute("SELECT rolcanlogin FROM pg_roles WHERE rolname = 'km_api'")
                assert cursor.fetchone() == (False,)
                cursor.execute("SELECT count(*) FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('users','farmer_profiles','partner_profiles','audit_logs')")
                assert cursor.fetchone() == (4,)
                cursor.execute("SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('users','farmer_profiles','partner_profiles','audit_logs')")
                assert all(enabled for _, enabled in cursor.fetchall())
                cursor.execute("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")
                indexes = {name for (name,) in cursor.fetchall()}
                assert {'users_pkey', 'users_mobile_number_key', 'users_role_tier_idx', 'farmer_profiles_user_id_key', 'audit_target_idx'} <= indexes

                for user_id, mobile in ((user_a, '9876543210'), (user_b, '9876543211')):
                    cursor.execute("INSERT INTO users (id,mobile_number,role,account_state,is_verified) VALUES (%s,%s,'farmer','active',TRUE)", (user_id, mobile))
                cursor.execute("INSERT INTO farmer_profiles (user_id,farmer_code,full_name,village,taluka,district) VALUES (%s,'A','Farmer A','V','T','D')", (user_a,))
                cursor.execute("INSERT INTO farmer_profiles (user_id,farmer_code,full_name,village,taluka,district) VALUES (%s,'B','Farmer B','V','T','D')", (user_b,))

                with pytest.raises(psycopg.errors.UniqueViolation):
                    cursor.execute("INSERT INTO users (mobile_number) VALUES ('9876543210')")
                with pytest.raises(psycopg.errors.CheckViolation):
                    cursor.execute("INSERT INTO users (mobile_number) VALUES ('not-a-number')")
                with pytest.raises(psycopg.errors.ForeignKeyViolation):
                    cursor.execute("INSERT INTO farmer_profiles (user_id,farmer_code,full_name,village,taluka,district) VALUES (%s,'C','C','V','T','D')", (uuid4(),))
                with pytest.raises(psycopg.errors.CheckViolation):
                    cursor.execute("INSERT INTO farmer_profiles (user_id,farmer_code,full_name,preferred_language,village,taluka,district) VALUES (%s,'C','C','xx','V','T','D')", (user_a,))

                # Grant SELECT temporarily so empty results prove RLS, not just
                # missing table privilege. The migration grants no direct SELECT.
                cursor.execute("GRANT km_api TO CURRENT_USER")
                cursor.execute("GRANT SELECT ON farmer_profiles TO km_api")
                cursor.execute("SET ROLE km_api")
                try:
                    cursor.execute("SELECT current_user")
                    assert cursor.fetchone() == ('km_api',)
                    cursor.execute("SELECT count(*) FROM farmer_profiles")
                    assert cursor.fetchone() == (0,)
                    with pytest.raises(psycopg.errors.InsufficientPrivilege):
                        cursor.execute("SELECT * FROM users")
                    with pytest.raises(psycopg.errors.InsufficientPrivilege):
                        cursor.execute("UPDATE farmer_profiles SET full_name='stolen' WHERE user_id=%s", (user_b,))
                    cursor.execute("SELECT id FROM km_private.lookup_actor(%s)", (user_a,))
                    assert cursor.fetchone() == (user_a,)
                finally:
                    cursor.execute("RESET ROLE")
                cursor.execute("REVOKE SELECT ON farmer_profiles FROM km_api")
                cursor.execute("REVOKE km_api FROM CURRENT_USER")
            finally:
                cursor.execute("RESET ROLE")
                cursor.execute("REVOKE SELECT ON farmer_profiles FROM km_api")
                cursor.execute("REVOKE km_api FROM CURRENT_USER")
                cursor.execute(down)
            cursor.execute("SELECT to_regclass('public.users')")
            assert cursor.fetchone() == (None,)
