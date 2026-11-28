-- Disposable local/staging rollback only; deletes all foundation records.
BEGIN;
DROP FUNCTION km_private.lookup_actor(UUID);
DROP FUNCTION km_private.lookup_actor_by_mobile(TEXT);
DROP TABLE audit_logs;
DROP TABLE partner_profiles;
DROP TABLE farmer_profiles;
DROP TABLE users;
DROP TYPE account_state_enum;
DROP TYPE account_tier_enum;
DROP TYPE user_role_enum;
DROP ROLE km_api;
DROP SCHEMA km_private;
COMMIT;
