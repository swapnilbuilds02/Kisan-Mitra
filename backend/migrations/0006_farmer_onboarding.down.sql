-- Disposable test rollback only; removes onboarding records from the isolated database.
BEGIN;
DROP FUNCTION km_private.update_farmer_profile(UUID,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT);
DROP FUNCTION km_private.farmer_profile_for(UUID);
DROP FUNCTION km_private.complete_farmer_onboarding(TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT);
DROP FUNCTION km_private.consume_onboarding_otp(UUID,TEXT,TEXT);
DROP FUNCTION km_private.farmer_onboarding_target(TEXT);
DROP TABLE km_private.farmer_onboarding_authorizations;
DROP TABLE public.farmer_consents;
DROP TABLE km_private.consent_documents;
ALTER TABLE public.farmer_profiles DROP COLUMN profile_completed_at;
COMMIT;
