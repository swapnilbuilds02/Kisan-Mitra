-- Disposable test rollback only. Revoke role membership before dropping 0001.
BEGIN;
DROP FUNCTION km_private.consume_otp(TEXT, TEXT, TEXT);
DROP FUNCTION km_private.issue_otp(TEXT, TEXT, TEXT, TEXT);
DROP FUNCTION km_private.revoke_user_sessions(UUID);
DROP FUNCTION km_private.revoke_session(UUID);
DROP FUNCTION km_private.rotate_session(UUID, TEXT, TEXT, INTEGER);
DROP FUNCTION km_private.session_active(UUID, UUID);
DROP FUNCTION km_private.create_session(UUID, TEXT, INTEGER);
DROP TABLE auth_security_events;
DROP TABLE auth_otp_requests;
DROP TABLE auth_otp_challenges;
DROP TABLE auth_refresh_history;
DROP TABLE auth_sessions;
COMMIT;
