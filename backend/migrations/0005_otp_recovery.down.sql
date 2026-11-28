-- Disposable test rollback only; previously issued OTPs cannot be restored.
BEGIN;
DROP FUNCTION km_private.change_password_credential(UUID,TEXT,TEXT);
DROP FUNCTION km_private.create_password_session(UUID,TEXT,INTEGER,TEXT);
DROP FUNCTION km_private.complete_password_reset(TEXT,TEXT);
DROP FUNCTION km_private.consume_reset_otp(UUID,TEXT,TEXT);
DROP FUNCTION km_private.issue_purpose_otp(TEXT,TEXT,TEXT,TEXT,TEXT,UUID);
DROP TABLE km_private.password_reset_authorizations;
ALTER TABLE public.auth_otp_challenges DROP COLUMN created_at;
ALTER TABLE public.auth_otp_challenges DROP COLUMN user_id;
ALTER TABLE public.auth_otp_challenges DROP COLUMN purpose;
ALTER TABLE public.auth_otp_challenges DROP COLUMN id;
-- Original issue_otp/consume_otp definitions must be restored from migration 0002
-- before this rollback is used in an environment that will continue accepting OTPs.
COMMIT;
