-- Additive Farmer onboarding. Apply after 0005 with migration-owner privileges.
BEGIN;
ALTER TABLE public.farmer_profiles ADD COLUMN profile_completed_at TIMESTAMPTZ;
CREATE TABLE km_private.consent_documents (
  document_id TEXT NOT NULL,
  version TEXT NOT NULL,
  approved_for_use BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY(document_id,version)
);
CREATE TABLE public.farmer_consents (
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
  document_id TEXT NOT NULL,
  version TEXT NOT NULL,
  acknowledged_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY(user_id,document_id,version),
  FOREIGN KEY(document_id,version) REFERENCES km_private.consent_documents(document_id,version)
);
CREATE TABLE km_private.farmer_onboarding_authorizations (
  token_hash CHAR(64) PRIMARY KEY CHECK(token_hash ~ '^[0-9a-f]{64}$'),
  mobile_number VARCHAR(15) NOT NULL CHECK(mobile_number ~ '^[6-9][0-9]{9}$'),
  user_id UUID REFERENCES public.users(id) ON DELETE RESTRICT,
  purpose TEXT NOT NULL CHECK(purpose IN ('REGISTRATION','ACCOUNT_CLAIM')),
  expires_at TIMESTAMPTZ NOT NULL,
  consumed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX farmer_onboarding_mobile_idx ON km_private.farmer_onboarding_authorizations(mobile_number,expires_at);
ALTER TABLE public.farmer_consents ENABLE ROW LEVEL SECURITY;
ALTER TABLE km_private.consent_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE km_private.farmer_onboarding_authorizations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.farmer_consents,km_private.consent_documents,km_private.farmer_onboarding_authorizations FROM PUBLIC;

CREATE FUNCTION km_private.farmer_onboarding_target(mobile TEXT)
RETURNS TABLE(subject UUID,otp_purpose TEXT) LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE candidate public.users%ROWTYPE;
BEGIN
  IF mobile !~ '^[6-9][0-9]{9}$' THEN RETURN; END IF;
  SELECT * INTO candidate FROM public.users WHERE mobile_number=mobile;
  IF NOT FOUND THEN RETURN QUERY SELECT NULL::UUID,'REGISTRATION'::TEXT; RETURN; END IF;
  IF candidate.role<>'farmer' OR NOT candidate.is_active OR candidate.account_state IN ('suspended','expired')
     OR EXISTS(SELECT 1 FROM km_private.password_credentials WHERE user_id=candidate.id) THEN RETURN; END IF;
  RETURN QUERY SELECT candidate.id,'ACCOUNT_CLAIM'::TEXT;
END $$;

CREATE FUNCTION km_private.consume_onboarding_otp(challenge UUID,code_digest TEXT,authorization_digest TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE challenge_row public.auth_otp_challenges%ROWTYPE;
BEGIN
  IF code_digest !~ '^[0-9a-f]{64}$' OR authorization_digest !~ '^[0-9a-f]{64}$' THEN RETURN FALSE; END IF;
  SELECT * INTO challenge_row FROM public.auth_otp_challenges WHERE id=challenge FOR UPDATE;
  IF NOT FOUND OR challenge_row.purpose NOT IN ('REGISTRATION','ACCOUNT_CLAIM')
     OR challenge_row.consumed_at IS NOT NULL OR challenge_row.expires_at<=clock_timestamp()
     OR challenge_row.attempts>=5 THEN RETURN FALSE; END IF;
  IF challenge_row.code_hash<>code_digest THEN
    UPDATE public.auth_otp_challenges SET attempts=attempts+1 WHERE id=challenge;
    INSERT INTO public.auth_security_events(action,mobile_hash) VALUES('OTP_INVALID',challenge_row.mobile_hash);
    RETURN FALSE;
  END IF;
  IF challenge_row.purpose='REGISTRATION' AND EXISTS(SELECT 1 FROM public.users WHERE mobile_number=challenge_row.mobile_number) THEN RETURN FALSE; END IF;
  IF challenge_row.purpose='ACCOUNT_CLAIM' AND NOT EXISTS(
    SELECT 1 FROM public.users WHERE id=challenge_row.user_id AND mobile_number=challenge_row.mobile_number
      AND role='farmer' AND is_active AND account_state NOT IN ('suspended','expired')
      AND NOT EXISTS(SELECT 1 FROM km_private.password_credentials WHERE user_id=challenge_row.user_id)) THEN RETURN FALSE; END IF;
  UPDATE public.auth_otp_challenges SET attempts=attempts+1,consumed_at=clock_timestamp(),code_hash=NULL WHERE id=challenge;
  INSERT INTO km_private.farmer_onboarding_authorizations(token_hash,mobile_number,user_id,purpose,expires_at)
    VALUES(authorization_digest,challenge_row.mobile_number,challenge_row.user_id,challenge_row.purpose,clock_timestamp()+interval '10 minutes');
  INSERT INTO public.auth_security_events(action,mobile_hash) VALUES('OTP_VERIFIED',challenge_row.mobile_hash);
  RETURN TRUE;
END $$;

CREATE FUNCTION km_private.complete_farmer_onboarding(
  authorization_digest TEXT,credential_hash TEXT,farmer_name TEXT,language_code TEXT,
  farmer_village TEXT,farmer_taluka TEXT,farmer_district TEXT,farmer_state TEXT,farmer_pincode TEXT,
  consent_id TEXT,consent_version TEXT)
RETURNS UUID LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE authrow km_private.farmer_onboarding_authorizations%ROWTYPE; farmer_id UUID;
BEGIN
  IF authorization_digest !~ '^[0-9a-f]{64}$' OR credential_hash !~ '^scrypt\$16384\$8\$1\$'
     OR length(trim(coalesce(farmer_name,'')))<2 OR length(trim(coalesce(farmer_village,'')))<1
     OR length(trim(coalesce(farmer_taluka,'')))<1 OR length(trim(coalesce(farmer_district,'')))<1
     OR language_code NOT IN ('mr','en') THEN RETURN NULL; END IF;
  IF NOT EXISTS(SELECT 1 FROM km_private.consent_documents WHERE document_id=consent_id AND version=consent_version AND approved_for_use) THEN RETURN NULL; END IF;
  SELECT * INTO authrow FROM km_private.farmer_onboarding_authorizations WHERE token_hash=authorization_digest FOR UPDATE;
  IF NOT FOUND OR authrow.consumed_at IS NOT NULL OR authrow.expires_at<=clock_timestamp() THEN RETURN NULL; END IF;
  PERFORM pg_advisory_xact_lock(hashtextextended('farmer:'||authrow.mobile_number,0));
  IF authrow.purpose='REGISTRATION' THEN
    IF EXISTS(SELECT 1 FROM public.users WHERE mobile_number=authrow.mobile_number) THEN RETURN NULL; END IF;
    INSERT INTO public.users(mobile_number,role,account_state,is_verified)
      VALUES(authrow.mobile_number,'farmer','active',TRUE) RETURNING id INTO farmer_id;
  ELSE
    SELECT id INTO farmer_id FROM public.users WHERE id=authrow.user_id AND mobile_number=authrow.mobile_number
      AND role='farmer' AND is_active AND account_state NOT IN ('suspended','expired') FOR UPDATE;
    IF farmer_id IS NULL THEN RETURN NULL; END IF;
  END IF;
  IF EXISTS(SELECT 1 FROM km_private.password_credentials WHERE user_id=farmer_id) THEN RETURN NULL; END IF;
  INSERT INTO km_private.password_credentials(user_id,password_hash) VALUES(farmer_id,credential_hash);
  INSERT INTO public.farmer_profiles(user_id,farmer_code,full_name,preferred_language,village,taluka,district,state,pincode,profile_completed_at)
    VALUES(farmer_id,'KM-'||left(replace(farmer_id::TEXT,'-',''),27),trim(farmer_name),language_code,
      trim(farmer_village),trim(farmer_taluka),trim(farmer_district),trim(farmer_state),nullif(trim(farmer_pincode),''),clock_timestamp())
    ON CONFLICT(user_id) DO UPDATE SET full_name=EXCLUDED.full_name,preferred_language=EXCLUDED.preferred_language,
      village=EXCLUDED.village,taluka=EXCLUDED.taluka,district=EXCLUDED.district,state=EXCLUDED.state,
      pincode=EXCLUDED.pincode,profile_completed_at=clock_timestamp();
  INSERT INTO public.farmer_consents(user_id,document_id,version)
    VALUES(farmer_id,consent_id,consent_version);
  UPDATE public.users SET is_verified=TRUE,account_state='active',updated_at=clock_timestamp() WHERE id=farmer_id;
  UPDATE km_private.farmer_onboarding_authorizations SET consumed_at=clock_timestamp()
    WHERE mobile_number=authrow.mobile_number AND consumed_at IS NULL;
  INSERT INTO public.audit_logs(actor_user_id,action,target_entity,target_id,reason)
    VALUES(farmer_id,'FARMER_ONBOARDED','users',farmer_id,authrow.purpose);
  RETURN farmer_id;
END $$;

CREATE FUNCTION km_private.farmer_profile_for(subject UUID)
RETURNS TABLE(full_name VARCHAR,preferred_language VARCHAR,village VARCHAR,taluka VARCHAR,district VARCHAR,state VARCHAR,pincode VARCHAR,profile_completed_at TIMESTAMPTZ)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public SET row_security=off AS $$
  SELECT full_name,preferred_language,village,taluka,district,state,pincode,profile_completed_at
  FROM public.farmer_profiles WHERE user_id=subject
$$;
CREATE FUNCTION km_private.update_farmer_profile(subject UUID,new_name TEXT,new_language TEXT,new_village TEXT,new_taluka TEXT,new_district TEXT,new_state TEXT,new_pincode TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public SET row_security=off AS $$
BEGIN
  IF new_language NOT IN ('mr','en') OR length(trim(new_name))<2 THEN RETURN FALSE; END IF;
  UPDATE public.farmer_profiles SET full_name=trim(new_name),preferred_language=new_language,
    village=trim(new_village),taluka=trim(new_taluka),district=trim(new_district),state=trim(new_state),
    pincode=nullif(trim(new_pincode),''),updated_at=clock_timestamp() WHERE user_id=subject;
  RETURN FOUND;
END $$;
REVOKE ALL ON FUNCTION km_private.farmer_onboarding_target(TEXT),
 km_private.consume_onboarding_otp(UUID,TEXT,TEXT),
 km_private.complete_farmer_onboarding(TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT),
 km_private.farmer_profile_for(UUID),km_private.update_farmer_profile(UUID,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION km_private.farmer_onboarding_target(TEXT),
 km_private.consume_onboarding_otp(UUID,TEXT,TEXT),
 km_private.complete_farmer_onboarding(TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT),
 km_private.farmer_profile_for(UUID),km_private.update_farmer_profile(UUID,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT) TO km_api;
COMMIT;
