-- Disposable verification rollback only; preserve application history in production.
BEGIN;
DROP FUNCTION km_private.issue_partner_reset_otp(TEXT,TEXT,TEXT,TEXT,UUID);
DROP FUNCTION km_private.consume_partner_login_otp(UUID,TEXT,UUID,TEXT);
DROP FUNCTION km_private.create_partner_session(UUID,TEXT,INTEGER);
DROP FUNCTION km_private.update_partner_location(UUID,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT);
DROP FUNCTION km_private.partner_decision_history(UUID);
DROP FUNCTION km_private.partner_application_detail(UUID);
DROP FUNCTION km_private.partner_application_for_user(UUID);
DROP FUNCTION km_private.partner_decision(UUID,UUID,TEXT,TEXT);
DROP FUNCTION km_private.pending_partner_applications(TEXT);
DROP FUNCTION km_private.partner_state(UUID);
DROP FUNCTION km_private.complete_partner_application(TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT);
DROP FUNCTION km_private.consume_partner_registration_otp(UUID,TEXT,TEXT,TEXT);
DROP FUNCTION km_private.partner_registration_eligible(TEXT);
DROP FUNCTION km_private.issue_partner_otp(TEXT,TEXT,TEXT,TEXT,TEXT);
DROP TABLE km_private.partner_onboarding_authorizations;
DROP TABLE public.partner_consents;
DROP TABLE public.partner_decisions;
DROP TABLE public.partner_applications;
ALTER TABLE public.auth_otp_challenges DROP COLUMN intended_partner_role;
-- Restore 0006 consume_onboarding_otp before continuing to accept Farmer OTPs.
COMMIT;
