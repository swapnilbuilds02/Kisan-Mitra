-- Additive partner applications; apply after 0006 on a disposable cluster first.
BEGIN;
ALTER TABLE public.auth_otp_challenges ADD COLUMN intended_partner_role user_role_enum;
CREATE OR REPLACE FUNCTION km_private.issue_purpose_otp(mobile TEXT,mobile_digest TEXT,ip_digest TEXT,code_digest TEXT,otp_purpose TEXT,subject UUID)
RETURNS UUID LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE now_at TIMESTAMPTZ:=clock_timestamp(); challenge UUID:=gen_random_uuid();
BEGIN
 IF mobile !~ '^[6-9][0-9]{9}$' OR mobile_digest !~ '^[0-9a-f]{64}$' OR ip_digest !~ '^[0-9a-f]{64}$'
   OR code_digest !~ '^[0-9a-f]{64}$' OR otp_purpose NOT IN ('REGISTRATION','LOGIN','ACCOUNT_CLAIM','PASSWORD_RESET') THEN RETURN NULL; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('otp:'||mobile,0));
 IF (SELECT count(*) FROM public.auth_otp_requests WHERE mobile_hash=mobile_digest AND created_at>now_at-interval '1 hour')>=3
   OR (SELECT count(*) FROM public.auth_otp_requests WHERE ip_hash=ip_digest AND created_at>now_at-interval '1 hour')>=3
   OR EXISTS(SELECT 1 FROM public.auth_otp_challenges WHERE mobile_number=mobile AND next_request_at>now_at) THEN RETURN NULL; END IF;
 INSERT INTO public.auth_otp_requests(mobile_hash,ip_hash) VALUES(mobile_digest,ip_digest);
 IF otp_purpose='PASSWORD_RESET' AND NOT EXISTS(SELECT 1 FROM public.users u JOIN km_private.password_credentials c ON c.user_id=u.id
   WHERE u.id=subject AND u.mobile_number=mobile AND u.is_verified AND u.is_active AND u.account_state='active' AND u.role='farmer') THEN RETURN NULL; END IF;
 INSERT INTO public.auth_otp_challenges(mobile_number,mobile_hash,code_hash,expires_at,next_request_at,attempts,consumed_at,id,purpose,user_id,created_at,intended_partner_role)
 VALUES(mobile,mobile_digest,code_digest,now_at+interval '120 seconds',now_at+interval '60 seconds',0,NULL,challenge,otp_purpose,subject,now_at,NULL)
 ON CONFLICT(mobile_number) DO UPDATE SET mobile_hash=EXCLUDED.mobile_hash,code_hash=EXCLUDED.code_hash,
   expires_at=EXCLUDED.expires_at,next_request_at=EXCLUDED.next_request_at,attempts=0,consumed_at=NULL,
   id=EXCLUDED.id,purpose=EXCLUDED.purpose,user_id=EXCLUDED.user_id,created_at=now_at,intended_partner_role=NULL;
 RETURN challenge;
END $$;
CREATE FUNCTION km_private.issue_partner_otp(mobile TEXT,mobile_digest TEXT,ip_digest TEXT,code_digest TEXT,intended_role TEXT)
RETURNS UUID LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public SET row_security=off AS $$
DECLARE challenge UUID;
BEGIN
 IF intended_role NOT IN ('shop','consultant') OR EXISTS(SELECT 1 FROM public.users WHERE mobile_number=mobile) THEN RETURN NULL; END IF;
 SELECT km_private.issue_purpose_otp(mobile,mobile_digest,ip_digest,code_digest,'REGISTRATION',NULL) INTO challenge;
 IF challenge IS NOT NULL THEN
  UPDATE public.auth_otp_challenges SET intended_partner_role=intended_role::user_role_enum WHERE id=challenge;
 END IF;
 RETURN challenge;
END $$;
CREATE OR REPLACE FUNCTION km_private.consume_onboarding_otp(challenge UUID,code_digest TEXT,authorization_digest TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE row public.auth_otp_challenges%ROWTYPE;
BEGIN
 IF code_digest !~ '^[0-9a-f]{64}$' OR authorization_digest !~ '^[0-9a-f]{64}$' THEN RETURN FALSE; END IF;
 SELECT * INTO row FROM public.auth_otp_challenges WHERE id=challenge FOR UPDATE;
 IF NOT FOUND OR row.intended_partner_role IS NOT NULL OR row.purpose NOT IN ('REGISTRATION','ACCOUNT_CLAIM')
   OR row.consumed_at IS NOT NULL OR row.expires_at<=clock_timestamp() OR row.attempts>=5 THEN RETURN FALSE; END IF;
 IF row.code_hash<>code_digest THEN
   UPDATE public.auth_otp_challenges SET attempts=attempts+1 WHERE id=challenge; RETURN FALSE;
 END IF;
 IF row.purpose='REGISTRATION' AND EXISTS(SELECT 1 FROM public.users WHERE mobile_number=row.mobile_number) THEN RETURN FALSE; END IF;
 IF row.purpose='ACCOUNT_CLAIM' AND NOT EXISTS(SELECT 1 FROM public.users WHERE id=row.user_id
   AND mobile_number=row.mobile_number AND role='farmer' AND is_active AND account_state NOT IN ('suspended','expired')
   AND NOT EXISTS(SELECT 1 FROM km_private.password_credentials WHERE user_id=row.user_id)) THEN RETURN FALSE; END IF;
 UPDATE public.auth_otp_challenges SET attempts=attempts+1,consumed_at=clock_timestamp(),code_hash=NULL WHERE id=challenge;
 INSERT INTO km_private.farmer_onboarding_authorizations(token_hash,mobile_number,user_id,purpose,expires_at)
 VALUES(authorization_digest,row.mobile_number,row.user_id,row.purpose,clock_timestamp()+interval '10 minutes');
 RETURN TRUE;
END $$;
CREATE TABLE public.partner_applications (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id UUID NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE RESTRICT,
 partner_role user_role_enum NOT NULL CHECK(partner_role IN ('shop','consultant')),
 status TEXT NOT NULL DEFAULT 'pending_approval' CHECK(status IN ('pending_approval','approved','rejected','suspended')),
 display_name VARCHAR(150) NOT NULL,
 representative_name VARCHAR(150),
 specialization VARCHAR(150),
 organization_name VARCHAR(150),
 preferred_language VARCHAR(10) NOT NULL CHECK(preferred_language IN ('mr','en')),
 state VARCHAR(100) NOT NULL, district VARCHAR(100) NOT NULL, taluka VARCHAR(100) NOT NULL,
 locality VARCHAR(100) NOT NULL, address VARCHAR(300), pincode VARCHAR(10),
 submitted_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 decided_at TIMESTAMPTZ, updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX partner_applications_queue_idx ON public.partner_applications(status,partner_role,submitted_at);
CREATE TABLE public.partner_decisions (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 application_id UUID NOT NULL REFERENCES public.partner_applications(id) ON DELETE RESTRICT,
 actor_id UUID NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
 prior_status TEXT NOT NULL,new_status TEXT NOT NULL,reason TEXT NOT NULL,
 decided_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX partner_decisions_history_idx ON public.partner_decisions(application_id,decided_at DESC);
CREATE TABLE public.partner_consents (
 user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
 document_id TEXT NOT NULL,version TEXT NOT NULL,
 acknowledged_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(user_id,document_id,version),
 FOREIGN KEY(document_id,version) REFERENCES km_private.consent_documents(document_id,version)
);
CREATE TABLE km_private.partner_onboarding_authorizations (
 token_hash CHAR(64) PRIMARY KEY CHECK(token_hash ~ '^[0-9a-f]{64}$'),
 mobile_number VARCHAR(15) NOT NULL,
 partner_role user_role_enum NOT NULL CHECK(partner_role IN ('shop','consultant')),
 expires_at TIMESTAMPTZ NOT NULL,
 consumed_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX partner_onboarding_mobile_idx ON km_private.partner_onboarding_authorizations(mobile_number,expires_at);
ALTER TABLE public.partner_applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.partner_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.partner_consents ENABLE ROW LEVEL SECURITY;
ALTER TABLE km_private.partner_onboarding_authorizations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.partner_applications,public.partner_decisions,public.partner_consents,km_private.partner_onboarding_authorizations FROM PUBLIC;

CREATE FUNCTION km_private.partner_registration_eligible(mobile TEXT)
RETURNS BOOLEAN LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public SET row_security=off AS $$
 SELECT mobile ~ '^[6-9][0-9]{9}$' AND NOT EXISTS(SELECT 1 FROM public.users WHERE mobile_number=mobile)
$$;
CREATE FUNCTION km_private.consume_partner_registration_otp(challenge UUID,code_digest TEXT,auth_digest TEXT,intended_role TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE row public.auth_otp_challenges%ROWTYPE;
BEGIN
 IF intended_role NOT IN ('shop','consultant') OR code_digest !~ '^[0-9a-f]{64}$' OR auth_digest !~ '^[0-9a-f]{64}$' THEN RETURN FALSE; END IF;
 SELECT * INTO row FROM public.auth_otp_challenges WHERE id=challenge FOR UPDATE;
 IF NOT FOUND OR row.purpose<>'REGISTRATION' OR row.intended_partner_role::TEXT<>intended_role
    OR row.user_id IS NOT NULL OR row.consumed_at IS NOT NULL
    OR row.expires_at<=clock_timestamp() OR row.attempts>=5 THEN RETURN FALSE; END IF;
 IF row.code_hash<>code_digest THEN
   UPDATE public.auth_otp_challenges SET attempts=attempts+1 WHERE id=challenge;
   RETURN FALSE;
 END IF;
 IF EXISTS(SELECT 1 FROM public.users WHERE mobile_number=row.mobile_number) THEN RETURN FALSE; END IF;
 UPDATE public.auth_otp_challenges SET attempts=attempts+1,consumed_at=clock_timestamp(),code_hash=NULL WHERE id=challenge;
 INSERT INTO km_private.partner_onboarding_authorizations(token_hash,mobile_number,partner_role,expires_at)
 VALUES(auth_digest,row.mobile_number,intended_role::user_role_enum,clock_timestamp()+interval '10 minutes');
 RETURN TRUE;
END $$;
CREATE FUNCTION km_private.complete_partner_application(auth_digest TEXT,credential_hash TEXT,role_name TEXT,
 display_text TEXT,representative_text TEXT,specialization_text TEXT,organization_text TEXT,language_code TEXT,
 state_text TEXT,district_text TEXT,taluka_text TEXT,locality_text TEXT,address_text TEXT,pincode_text TEXT,
 consent_id TEXT,consent_version TEXT)
RETURNS UUID LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE authrow km_private.partner_onboarding_authorizations%ROWTYPE; new_user UUID; new_app UUID;
BEGIN
 IF role_name NOT IN ('shop','consultant') OR credential_hash !~ '^scrypt\$16384\$8\$1\$'
    OR length(trim(coalesce(display_text,'')))<2 OR language_code NOT IN ('mr','en')
    OR length(trim(coalesce(district_text,'')))<1 OR length(trim(coalesce(taluka_text,'')))<1
    OR length(trim(coalesce(locality_text,'')))<1 THEN RETURN NULL; END IF;
 IF NOT EXISTS(SELECT 1 FROM km_private.consent_documents WHERE document_id=consent_id AND version=consent_version AND approved_for_use) THEN RETURN NULL; END IF;
 SELECT * INTO authrow FROM km_private.partner_onboarding_authorizations WHERE token_hash=auth_digest FOR UPDATE;
 IF NOT FOUND OR authrow.consumed_at IS NOT NULL OR authrow.expires_at<=clock_timestamp()
    OR authrow.partner_role::TEXT<>role_name THEN RETURN NULL; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('farmer:'||authrow.mobile_number,0));
 IF EXISTS(SELECT 1 FROM public.users WHERE mobile_number=authrow.mobile_number) THEN RETURN NULL; END IF;
 INSERT INTO public.users(mobile_number,role,account_state,is_verified)
   VALUES(authrow.mobile_number,role_name::user_role_enum,'pending_approval',TRUE) RETURNING id INTO new_user;
 INSERT INTO km_private.password_credentials(user_id,password_hash) VALUES(new_user,credential_hash);
 INSERT INTO public.partner_profiles(user_id,display_name,organization_name)
   VALUES(new_user,trim(display_text),nullif(trim(organization_text),''));
 INSERT INTO public.partner_applications(user_id,partner_role,display_name,representative_name,specialization,organization_name,
   preferred_language,state,district,taluka,locality,address,pincode)
 VALUES(new_user,role_name::user_role_enum,trim(display_text),nullif(trim(representative_text),''),
   nullif(trim(specialization_text),''),nullif(trim(organization_text),''),language_code,trim(state_text),
   trim(district_text),trim(taluka_text),trim(locality_text),nullif(trim(address_text),''),nullif(trim(pincode_text),'')) RETURNING id INTO new_app;
 INSERT INTO public.partner_consents(user_id,document_id,version) VALUES(new_user,consent_id,consent_version);
 UPDATE km_private.partner_onboarding_authorizations SET consumed_at=clock_timestamp()
   WHERE mobile_number=authrow.mobile_number AND consumed_at IS NULL;
 INSERT INTO public.audit_logs(actor_user_id,action,target_entity,target_id,reason)
   VALUES(new_user,'PARTNER_APPLICATION_SUBMITTED','partner_applications',new_app,role_name);
 RETURN new_user;
END $$;

CREATE FUNCTION km_private.partner_state(subject UUID)
RETURNS TABLE(application_id UUID,partner_role user_role_enum,status TEXT,display_name VARCHAR,preferred_language VARCHAR,
 state VARCHAR,district VARCHAR,taluka VARCHAR,locality VARCHAR,address VARCHAR,pincode VARCHAR)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public SET row_security=off AS $$
 SELECT id,partner_role,status,display_name,preferred_language,state,district,taluka,locality,address,pincode
 FROM public.partner_applications WHERE user_id=subject
$$;
CREATE FUNCTION km_private.partner_application_detail(app UUID)
RETURNS TABLE(application_id UUID,user_id UUID,partner_role user_role_enum,status TEXT,display_name VARCHAR,
 representative_name VARCHAR,specialization VARCHAR,organization_name VARCHAR,preferred_language VARCHAR,
 state VARCHAR,district VARCHAR,taluka VARCHAR,locality VARCHAR,address VARCHAR,pincode VARCHAR,submitted_at TIMESTAMPTZ)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public SET row_security=off AS $$
 SELECT id,user_id,partner_role,status,display_name,representative_name,specialization,organization_name,
 preferred_language,state,district,taluka,locality,address,pincode,submitted_at
 FROM public.partner_applications WHERE id=app
$$;
CREATE FUNCTION km_private.partner_application_for_user(subject UUID)
RETURNS UUID LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public SET row_security=off AS $$
 SELECT id FROM public.partner_applications WHERE user_id=subject
$$;
CREATE FUNCTION km_private.partner_decision_history(app UUID)
RETURNS TABLE(prior_status TEXT,new_status TEXT,reason TEXT,actor_id UUID,decided_at TIMESTAMPTZ)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public SET row_security=off AS $$
 SELECT prior_status,new_status,reason,actor_id,decided_at FROM public.partner_decisions
 WHERE application_id=app ORDER BY decided_at
$$;
CREATE FUNCTION km_private.update_partner_location(subject UUID,language_code TEXT,state_text TEXT,district_text TEXT,
 taluka_text TEXT,locality_text TEXT,address_text TEXT,pincode_text TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public SET row_security=off AS $$
BEGIN
 IF language_code NOT IN ('mr','en') OR length(trim(coalesce(district_text,'')))<1 THEN RETURN FALSE; END IF;
 UPDATE public.partner_applications SET preferred_language=language_code,state=trim(state_text),
 district=trim(district_text),taluka=trim(taluka_text),locality=trim(locality_text),
 address=nullif(trim(address_text),''),pincode=nullif(trim(pincode_text),''),updated_at=clock_timestamp()
 WHERE user_id=subject AND status IN ('pending_approval','approved');
 RETURN FOUND;
END $$;
CREATE FUNCTION km_private.pending_partner_applications(role_filter TEXT)
RETURNS TABLE(application_id UUID,user_id UUID,partner_role user_role_enum,status TEXT,display_name VARCHAR,submitted_at TIMESTAMPTZ)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public SET row_security=off AS $$
 SELECT id,user_id,partner_role,status,display_name,submitted_at FROM public.partner_applications
 WHERE status='pending_approval' AND (role_filter IS NULL OR partner_role::TEXT=role_filter) ORDER BY submitted_at LIMIT 100
$$;
CREATE FUNCTION km_private.partner_decision(app UUID,operator UUID,action_name TEXT,decision_reason TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public SET row_security=off AS $$
DECLARE row public.partner_applications%ROWTYPE; next_status TEXT;
BEGIN
 IF length(trim(coalesce(decision_reason,'')))<5 THEN RETURN FALSE; END IF;
 PERFORM 1 FROM public.users WHERE id=operator AND is_active AND is_verified AND account_state='active'
   AND role IN ('admin','super_admin') FOR UPDATE;
 IF NOT FOUND THEN RETURN FALSE; END IF;
 SELECT * INTO row FROM public.partner_applications WHERE id=app FOR UPDATE;
 IF NOT FOUND THEN RETURN FALSE; END IF;
 next_status:=CASE
   WHEN row.status='pending_approval' AND action_name='approve' THEN 'approved'
   WHEN row.status='pending_approval' AND action_name='reject' THEN 'rejected'
   WHEN row.status='approved' AND action_name='suspend' THEN 'suspended'
   WHEN row.status='suspended' AND action_name='reactivate' THEN 'approved'
   ELSE NULL END;
 IF next_status IS NULL THEN RETURN FALSE; END IF;
 UPDATE public.partner_applications SET status=next_status,decided_at=clock_timestamp(),updated_at=clock_timestamp() WHERE id=app;
 UPDATE public.users SET account_state=CASE WHEN next_status='approved' THEN 'active' WHEN next_status='suspended' THEN 'suspended' ELSE 'pending_approval' END::account_state_enum,
  updated_at=clock_timestamp() WHERE id=row.user_id;
 UPDATE public.auth_sessions SET revoked_at=clock_timestamp() WHERE user_id=row.user_id AND revoked_at IS NULL;
 INSERT INTO public.partner_decisions(application_id,actor_id,prior_status,new_status,reason)
   VALUES(app,operator,row.status,next_status,decision_reason);
 INSERT INTO public.audit_logs(actor_user_id,action,target_entity,target_id,reason,old_state,new_state)
   VALUES(operator,'PARTNER_DECISION','partner_applications',app,decision_reason,
    jsonb_build_object('status',row.status),jsonb_build_object('status',next_status));
 RETURN TRUE;
END $$;
CREATE OR REPLACE FUNCTION km_private.create_password_session(subject UUID,digest TEXT,ttl_seconds INTEGER,credential_hash TEXT)
RETURNS UUID LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE new_id UUID; account public.users%ROWTYPE;
BEGIN
 IF ttl_seconds<1 OR ttl_seconds>2592000 OR digest !~ '^[0-9a-f]{64}$' THEN RETURN NULL; END IF;
 SELECT * INTO account FROM public.users WHERE id=subject FOR UPDATE;
 IF NOT FOUND OR NOT account.is_active OR NOT account.is_verified OR
    NOT EXISTS(SELECT 1 FROM km_private.password_credentials WHERE user_id=subject AND password_hash=credential_hash) THEN RETURN NULL; END IF;
 IF account.role='farmer' AND account.account_state<>'active' THEN RETURN NULL; END IF;
 IF account.role IN ('shop','consultant') AND NOT EXISTS(
    SELECT 1 FROM public.partner_applications WHERE user_id=subject AND partner_role=account.role
      AND status IN ('pending_approval','approved') AND
      ((status='pending_approval' AND account.account_state='pending_approval') OR
       (status='approved' AND account.account_state='active'))) THEN RETURN NULL; END IF;
 IF account.role NOT IN ('farmer','shop','consultant') THEN RETURN NULL; END IF;
 INSERT INTO public.auth_sessions(user_id,refresh_hash,expires_at)
 VALUES(subject,digest,clock_timestamp()+make_interval(secs=>ttl_seconds)) RETURNING id INTO new_id;
 INSERT INTO public.auth_security_events(action,session_id) VALUES('SESSION_CREATED',new_id);
 RETURN new_id;
END $$;
CREATE FUNCTION km_private.create_partner_session(subject UUID,digest TEXT,ttl_seconds INTEGER)
RETURNS UUID LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public SET row_security=off AS $$
DECLARE new_id UUID; account public.users%ROWTYPE;
BEGIN
 IF ttl_seconds<1 OR ttl_seconds>2592000 OR digest !~ '^[0-9a-f]{64}$' THEN RETURN NULL; END IF;
 SELECT * INTO account FROM public.users WHERE id=subject FOR UPDATE;
 IF NOT FOUND OR NOT account.is_active OR NOT account.is_verified OR account.role NOT IN ('shop','consultant') THEN RETURN NULL; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.partner_applications WHERE user_id=subject AND partner_role=account.role
   AND ((status='pending_approval' AND account.account_state='pending_approval') OR
        (status='approved' AND account.account_state='active'))) THEN RETURN NULL; END IF;
 INSERT INTO public.auth_sessions(user_id,refresh_hash,expires_at)
 VALUES(subject,digest,clock_timestamp()+make_interval(secs=>ttl_seconds)) RETURNING id INTO new_id;
 INSERT INTO public.auth_security_events(action,session_id) VALUES('SESSION_CREATED',new_id);
 RETURN new_id;
END $$;
CREATE FUNCTION km_private.consume_partner_login_otp(challenge UUID,mobile TEXT,subject UUID,code_digest TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public SET row_security=off AS $$
DECLARE row public.auth_otp_challenges%ROWTYPE;
BEGIN
 SELECT * INTO row FROM public.auth_otp_challenges WHERE id=challenge FOR UPDATE;
 IF NOT FOUND OR row.purpose<>'LOGIN' OR row.user_id<>subject OR row.mobile_number<>mobile
   OR row.consumed_at IS NOT NULL OR row.expires_at<=clock_timestamp() OR row.attempts>=5 THEN RETURN FALSE; END IF;
 IF row.code_hash<>code_digest THEN
   UPDATE public.auth_otp_challenges SET attempts=attempts+1 WHERE id=challenge; RETURN FALSE;
 END IF;
 UPDATE public.auth_otp_challenges SET attempts=attempts+1,consumed_at=clock_timestamp(),code_hash=NULL WHERE id=challenge;
 RETURN TRUE;
END $$;
CREATE FUNCTION km_private.issue_partner_reset_otp(mobile TEXT,mobile_digest TEXT,ip_digest TEXT,code_digest TEXT,subject UUID)
RETURNS UUID LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE challenge UUID:=gen_random_uuid(); now_at TIMESTAMPTZ:=clock_timestamp();
BEGIN
 IF mobile !~ '^[6-9][0-9]{9}$' OR mobile_digest !~ '^[0-9a-f]{64}$' OR ip_digest !~ '^[0-9a-f]{64}$'
   OR code_digest !~ '^[0-9a-f]{64}$' THEN RETURN NULL; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('otp:'||mobile,0));
 IF (SELECT count(*) FROM public.auth_otp_requests WHERE mobile_hash=mobile_digest AND created_at>now_at-interval '1 hour')>=3
   OR (SELECT count(*) FROM public.auth_otp_requests WHERE ip_hash=ip_digest AND created_at>now_at-interval '1 hour')>=3
   OR EXISTS(SELECT 1 FROM public.auth_otp_challenges WHERE mobile_number=mobile AND next_request_at>now_at) THEN RETURN NULL; END IF;
 INSERT INTO public.auth_otp_requests(mobile_hash,ip_hash) VALUES(mobile_digest,ip_digest);
 IF NOT EXISTS(SELECT 1 FROM public.users u JOIN public.partner_applications a ON a.user_id=u.id
   JOIN km_private.password_credentials c ON c.user_id=u.id WHERE u.id=subject AND u.mobile_number=mobile
   AND u.is_verified AND u.is_active AND u.role IN ('shop','consultant') AND a.partner_role=u.role
   AND ((a.status='pending_approval' AND u.account_state='pending_approval') OR
        (a.status='approved' AND u.account_state='active'))) THEN RETURN NULL; END IF;
 INSERT INTO public.auth_otp_challenges(mobile_number,mobile_hash,code_hash,expires_at,next_request_at,attempts,
   consumed_at,id,purpose,user_id,created_at)
 VALUES(mobile,mobile_digest,code_digest,now_at+interval '120 seconds',now_at+interval '60 seconds',0,
   NULL,challenge,'PASSWORD_RESET',subject,now_at)
 ON CONFLICT(mobile_number) DO UPDATE SET mobile_hash=EXCLUDED.mobile_hash,code_hash=EXCLUDED.code_hash,
   expires_at=EXCLUDED.expires_at,next_request_at=EXCLUDED.next_request_at,attempts=0,consumed_at=NULL,
   id=EXCLUDED.id,purpose='PASSWORD_RESET',user_id=subject,created_at=now_at,intended_partner_role=NULL;
 RETURN challenge;
END $$;
CREATE OR REPLACE FUNCTION km_private.complete_password_reset(authorization_digest TEXT,new_hash TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE authrow km_private.password_reset_authorizations%ROWTYPE; account public.users%ROWTYPE;
BEGIN
 IF new_hash !~ '^scrypt\$16384\$8\$1\$' OR length(new_hash)>512 THEN RETURN FALSE; END IF;
 SELECT * INTO authrow FROM km_private.password_reset_authorizations WHERE token_hash=authorization_digest FOR UPDATE;
 IF NOT FOUND OR authrow.consumed_at IS NOT NULL OR authrow.expires_at<=clock_timestamp() THEN RETURN FALSE; END IF;
 SELECT * INTO account FROM public.users WHERE id=authrow.user_id FOR UPDATE;
 IF NOT FOUND OR NOT account.is_verified OR NOT account.is_active THEN RETURN FALSE; END IF;
 IF account.role='farmer' AND account.account_state<>'active' THEN RETURN FALSE; END IF;
 IF account.role IN ('shop','consultant') AND NOT EXISTS(SELECT 1 FROM public.partner_applications
   WHERE user_id=account.id AND partner_role=account.role AND
   ((status='pending_approval' AND account.account_state='pending_approval') OR
    (status='approved' AND account.account_state='active'))) THEN RETURN FALSE; END IF;
 IF account.role NOT IN ('farmer','shop','consultant') THEN RETURN FALSE; END IF;
 IF EXISTS(SELECT 1 FROM km_private.password_reset_authorizations WHERE token_hash=authorization_digest AND consumed_at IS NOT NULL) THEN RETURN FALSE; END IF;
 UPDATE km_private.password_credentials SET password_hash=new_hash,updated_at=clock_timestamp() WHERE user_id=account.id;
 IF NOT FOUND THEN RETURN FALSE; END IF;
 UPDATE km_private.password_reset_authorizations SET consumed_at=clock_timestamp() WHERE user_id=account.id AND consumed_at IS NULL;
 UPDATE public.auth_sessions SET revoked_at=clock_timestamp() WHERE user_id=account.id AND revoked_at IS NULL;
 INSERT INTO public.auth_security_events(action) VALUES('USER_SESSIONS_REVOKED');
 INSERT INTO public.audit_logs(actor_user_id,action,target_entity,target_id,reason)
 VALUES(account.id,'PASSWORD_RESET','users',account.id,'OTP authorized');
 RETURN TRUE;
END $$;
CREATE OR REPLACE FUNCTION km_private.change_password_credential(subject UUID,old_hash TEXT,new_hash TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE account public.users%ROWTYPE;
BEGIN
 IF new_hash !~ '^scrypt\$16384\$8\$1\$' OR length(new_hash)>512 THEN RETURN FALSE; END IF;
 SELECT * INTO account FROM public.users WHERE id=subject FOR UPDATE;
 IF NOT FOUND OR NOT account.is_active OR NOT account.is_verified THEN RETURN FALSE; END IF;
 IF account.role='farmer' AND account.account_state<>'active' THEN RETURN FALSE; END IF;
 IF account.role IN ('shop','consultant') AND NOT EXISTS(SELECT 1 FROM public.partner_applications
   WHERE user_id=subject AND partner_role=account.role AND
   ((status='pending_approval' AND account.account_state='pending_approval') OR
    (status='approved' AND account.account_state='active'))) THEN RETURN FALSE; END IF;
 IF account.role NOT IN ('farmer','shop','consultant') THEN RETURN FALSE; END IF;
 UPDATE km_private.password_credentials SET password_hash=new_hash,updated_at=clock_timestamp()
 WHERE user_id=subject AND password_hash=old_hash;
 IF NOT FOUND THEN RETURN FALSE; END IF;
 UPDATE public.auth_sessions SET revoked_at=clock_timestamp() WHERE user_id=subject AND revoked_at IS NULL;
 INSERT INTO public.auth_security_events(action) VALUES('USER_SESSIONS_REVOKED');
 INSERT INTO public.audit_logs(actor_user_id,action,target_entity,target_id,reason)
 VALUES(subject,'PASSWORD_CHANGED','users',subject,'authenticated password change');
 RETURN TRUE;
END $$;
REVOKE ALL ON FUNCTION km_private.partner_registration_eligible(TEXT),
 km_private.issue_partner_otp(TEXT,TEXT,TEXT,TEXT,TEXT),
 km_private.consume_partner_registration_otp(UUID,TEXT,TEXT,TEXT),
 km_private.complete_partner_application(TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT),
 km_private.partner_state(UUID),km_private.partner_application_detail(UUID),km_private.partner_application_for_user(UUID),km_private.partner_decision_history(UUID),
 km_private.update_partner_location(UUID,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT),
 km_private.pending_partner_applications(TEXT),km_private.partner_decision(UUID,UUID,TEXT,TEXT),
 km_private.create_partner_session(UUID,TEXT,INTEGER),km_private.consume_partner_login_otp(UUID,TEXT,UUID,TEXT),
 km_private.issue_partner_reset_otp(TEXT,TEXT,TEXT,TEXT,UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION km_private.partner_registration_eligible(TEXT),
 km_private.issue_partner_otp(TEXT,TEXT,TEXT,TEXT,TEXT),
 km_private.consume_partner_registration_otp(UUID,TEXT,TEXT,TEXT),
 km_private.complete_partner_application(TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT),
 km_private.partner_state(UUID),km_private.partner_application_detail(UUID),km_private.partner_application_for_user(UUID),km_private.partner_decision_history(UUID),
 km_private.update_partner_location(UUID,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT),
 km_private.pending_partner_applications(TEXT),km_private.partner_decision(UUID,UUID,TEXT,TEXT),
 km_private.create_partner_session(UUID,TEXT,INTEGER),km_private.consume_partner_login_otp(UUID,TEXT,UUID,TEXT),
 km_private.issue_partner_reset_otp(TEXT,TEXT,TEXT,TEXT,UUID) TO km_api;
COMMIT;
