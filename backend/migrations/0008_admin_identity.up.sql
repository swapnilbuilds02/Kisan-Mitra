-- Restricted Admin provisioning, applied by a migration owner after 0007.
BEGIN;
CREATE TABLE km_private.admin_provisioning (
 user_id UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE RESTRICT,
 display_name VARCHAR(150) NOT NULL,
 provisioned_by UUID REFERENCES public.users(id) ON DELETE RESTRICT,
 mobile_verified_at TIMESTAMPTZ,
 activated_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 CHECK (activated_at IS NULL OR mobile_verified_at IS NOT NULL)
);
CREATE TABLE km_private.admin_onboarding_authorizations (
 token_hash CHAR(64) PRIMARY KEY CHECK(token_hash ~ '^[0-9a-f]{64}$'),
 user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
 expires_at TIMESTAMPTZ NOT NULL,
 consumed_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX admin_onboarding_user_idx ON km_private.admin_onboarding_authorizations(user_id,expires_at);
ALTER TABLE km_private.admin_provisioning ENABLE ROW LEVEL SECURITY;
ALTER TABLE km_private.admin_onboarding_authorizations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON km_private.admin_provisioning,km_private.admin_onboarding_authorizations FROM PUBLIC;

CREATE TABLE km_private.admin_auth_limits (
 scope TEXT NOT NULL CHECK(scope IN ('mobile','ip')),
 kind TEXT NOT NULL CHECK(kind IN ('password','otp')),
 subject_hash CHAR(64) NOT NULL CHECK(subject_hash ~ '^[0-9a-f]{64}$'),
 window_start TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 attempts INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(scope,kind,subject_hash)
);
ALTER TABLE km_private.admin_auth_limits ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON km_private.admin_auth_limits FROM PUBLIC;
CREATE FUNCTION km_private.admin_auth_attempt(mobile_digest TEXT,ip_digest TEXT,attempt_kind TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE scope_name TEXT; digest CHAR(64); count_now INTEGER; allowed BOOLEAN:=TRUE;
DECLARE window_length INTERVAL; max_attempts INTEGER;
BEGIN
 IF mobile_digest !~ '^[0-9a-f]{64}$' OR ip_digest !~ '^[0-9a-f]{64}$'
   OR attempt_kind NOT IN ('password','otp') THEN RETURN FALSE; END IF;
 window_length:=CASE WHEN attempt_kind='otp' THEN interval '1 hour' ELSE interval '15 minutes' END;
 max_attempts:=CASE WHEN attempt_kind='otp' THEN 2 ELSE 3 END;
 FOR scope_name,digest IN SELECT 'ip'::TEXT,ip_digest::CHAR(64)
   UNION ALL SELECT 'mobile'::TEXT,mobile_digest::CHAR(64) ORDER BY 1 LOOP
   INSERT INTO km_private.admin_auth_limits(scope,kind,subject_hash,attempts)
     VALUES(scope_name,attempt_kind,digest,1)
   ON CONFLICT(scope,kind,subject_hash) DO UPDATE SET
     attempts=CASE WHEN admin_auth_limits.window_start<clock_timestamp()-window_length THEN 1 ELSE admin_auth_limits.attempts+1 END,
     window_start=CASE WHEN admin_auth_limits.window_start<clock_timestamp()-window_length THEN clock_timestamp() ELSE admin_auth_limits.window_start END
   RETURNING attempts INTO count_now;
   IF count_now>max_attempts THEN allowed:=FALSE; END IF;
 END LOOP;
 RETURN allowed;
END $$;
REVOKE ALL ON FUNCTION km_private.admin_auth_attempt(TEXT,TEXT,TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION km_private.admin_auth_attempt(TEXT,TEXT,TEXT) TO km_api;

-- This function stays migration-owner-only. It never marks mobile verified or active.
CREATE FUNCTION km_private.prepare_admin(mobile TEXT,display_text TEXT,operator_id UUID,bootstrap BOOLEAN)
RETURNS UUID LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE new_id UUID; new_role user_role_enum;
BEGIN
 IF mobile !~ '^[6-9][0-9]{9}$' OR length(trim(coalesce(display_text,'')))<2 THEN RETURN NULL; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('identity:'||mobile,0));
 IF EXISTS(SELECT 1 FROM public.users WHERE mobile_number=mobile) THEN RETURN NULL; END IF;
 IF bootstrap THEN
   PERFORM pg_advisory_xact_lock(hashtextextended('admin-bootstrap',0));
   IF operator_id IS NOT NULL OR EXISTS(SELECT 1 FROM public.users WHERE role='super_admin') THEN RETURN NULL; END IF;
   new_role:='super_admin';
 ELSE
   IF NOT EXISTS(SELECT 1 FROM public.users u JOIN km_private.admin_provisioning p ON p.user_id=u.id
     WHERE u.id=operator_id AND u.role='super_admin' AND u.is_active AND u.is_verified
       AND u.account_state='active' AND p.activated_at IS NOT NULL) THEN RETURN NULL; END IF;
   new_role:='admin';
 END IF;
 INSERT INTO public.users(mobile_number,role,account_state,is_verified)
 VALUES(mobile,new_role,'pending_approval',FALSE) RETURNING id INTO new_id;
 INSERT INTO km_private.admin_provisioning(user_id,display_name,provisioned_by)
 VALUES(new_id,trim(display_text),operator_id);
 INSERT INTO public.audit_logs(actor_user_id,action,target_entity,target_id,reason)
 VALUES(operator_id,'ADMIN_PROVISION_PREPARED','users',new_id,CASE WHEN bootstrap THEN 'bootstrap' ELSE 'restricted operator' END);
 RETURN new_id;
END $$;
REVOKE ALL ON FUNCTION km_private.prepare_admin(TEXT,TEXT,UUID,BOOLEAN) FROM PUBLIC;

CREATE FUNCTION km_private.admin_provisioning_candidate(mobile TEXT)
RETURNS UUID LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
 SELECT u.id FROM public.users u JOIN km_private.admin_provisioning p ON p.user_id=u.id
 WHERE u.mobile_number=mobile AND u.role IN ('admin','super_admin') AND u.is_active AND u.account_state='pending_approval'
   AND NOT u.is_verified AND p.activated_at IS NULL
$$;
CREATE FUNCTION km_private.consume_admin_verification_otp(challenge UUID,mobile TEXT,code_digest TEXT,authorization_digest TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE row public.auth_otp_challenges%ROWTYPE;
BEGIN
 IF code_digest !~ '^[0-9a-f]{64}$' OR authorization_digest !~ '^[0-9a-f]{64}$' THEN RETURN FALSE; END IF;
 SELECT * INTO row FROM public.auth_otp_challenges WHERE id=challenge FOR UPDATE;
 IF NOT FOUND OR row.purpose<>'ACCOUNT_CLAIM' OR row.intended_partner_role IS NOT NULL OR row.user_id IS NULL OR row.mobile_number<>mobile
    OR row.consumed_at IS NOT NULL OR row.expires_at<=clock_timestamp() OR row.attempts>=5 THEN RETURN FALSE; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.users u JOIN km_private.admin_provisioning p ON p.user_id=u.id
   WHERE u.id=row.user_id AND u.mobile_number=mobile AND u.role IN ('admin','super_admin') AND u.is_active
     AND NOT u.is_verified AND u.account_state='pending_approval' AND p.activated_at IS NULL) THEN RETURN FALSE; END IF;
 IF row.code_hash<>code_digest THEN
   UPDATE public.auth_otp_challenges SET attempts=attempts+1 WHERE id=challenge; RETURN FALSE; END IF;
 UPDATE public.auth_otp_challenges SET attempts=attempts+1,consumed_at=clock_timestamp(),code_hash=NULL WHERE id=challenge;
 INSERT INTO km_private.admin_onboarding_authorizations(token_hash,user_id,expires_at)
 VALUES(authorization_digest,row.user_id,clock_timestamp()+interval '10 minutes');
 UPDATE km_private.admin_provisioning SET mobile_verified_at=clock_timestamp() WHERE user_id=row.user_id;
 INSERT INTO public.audit_logs(actor_user_id,action,target_entity,target_id,reason)
 VALUES(row.user_id,'ADMIN_MOBILE_VERIFIED','users',row.user_id,'OTP verified');
 RETURN TRUE;
END $$;
CREATE FUNCTION km_private.activate_admin(authorization_digest TEXT,credential_hash TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE authrow km_private.admin_onboarding_authorizations%ROWTYPE; account public.users%ROWTYPE;
BEGIN
 IF credential_hash !~ '^scrypt\$16384\$8\$1\$' OR length(credential_hash)>512 THEN RETURN FALSE; END IF;
 SELECT * INTO authrow FROM km_private.admin_onboarding_authorizations WHERE token_hash=authorization_digest FOR UPDATE;
 IF NOT FOUND OR authrow.consumed_at IS NOT NULL OR authrow.expires_at<=clock_timestamp() THEN RETURN FALSE; END IF;
 SELECT * INTO account FROM public.users WHERE id=authrow.user_id FOR UPDATE;
 IF NOT FOUND OR account.role NOT IN ('admin','super_admin') OR account.account_state<>'pending_approval'
   OR account.is_verified OR NOT account.is_active THEN RETURN FALSE; END IF;
 IF NOT EXISTS(SELECT 1 FROM km_private.admin_provisioning WHERE user_id=account.id AND mobile_verified_at IS NOT NULL AND activated_at IS NULL) THEN RETURN FALSE; END IF;
 INSERT INTO km_private.password_credentials(user_id,password_hash) VALUES(account.id,credential_hash);
 UPDATE public.users SET is_verified=TRUE,account_state='active',updated_at=clock_timestamp() WHERE id=account.id;
 UPDATE km_private.admin_provisioning SET activated_at=clock_timestamp() WHERE user_id=account.id;
 UPDATE km_private.admin_onboarding_authorizations SET consumed_at=clock_timestamp() WHERE user_id=account.id AND consumed_at IS NULL;
 INSERT INTO public.audit_logs(actor_user_id,action,target_entity,target_id,reason)
 VALUES(account.id,'ADMIN_ACTIVATED','users',account.id,'verified mobile and password');
 RETURN TRUE;
END $$;
REVOKE ALL ON FUNCTION km_private.admin_provisioning_candidate(TEXT),
 km_private.consume_admin_verification_otp(UUID,TEXT,TEXT,TEXT),km_private.activate_admin(TEXT,TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION km_private.admin_provisioning_candidate(TEXT),
 km_private.consume_admin_verification_otp(UUID,TEXT,TEXT,TEXT),km_private.activate_admin(TEXT,TEXT) TO km_api;

CREATE FUNCTION km_private.admin_active(subject UUID)
RETURNS BOOLEAN LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
 SELECT EXISTS(SELECT 1 FROM public.users u JOIN km_private.admin_provisioning p ON p.user_id=u.id
   WHERE u.id=subject AND u.role IN ('admin','super_admin') AND u.is_active AND u.is_verified
     AND u.account_state='active' AND p.mobile_verified_at IS NOT NULL AND p.activated_at IS NOT NULL)
$$;
REVOKE ALL ON FUNCTION km_private.admin_active(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION km_private.admin_active(UUID) TO km_api;

CREATE FUNCTION km_private.consume_admin_login_otp(challenge UUID,mobile TEXT,subject UUID,code_digest TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE row public.auth_otp_challenges%ROWTYPE;
BEGIN
 SELECT * INTO row FROM public.auth_otp_challenges WHERE id=challenge FOR UPDATE;
 IF NOT FOUND OR row.purpose<>'LOGIN' OR row.intended_partner_role IS NOT NULL OR row.user_id<>subject OR row.mobile_number<>mobile
   OR row.consumed_at IS NOT NULL OR row.expires_at<=clock_timestamp() OR row.attempts>=5
   OR NOT km_private.admin_active(subject) THEN
   INSERT INTO public.auth_security_events(action,mobile_hash) VALUES('OTP_INVALID',row.mobile_hash);
   RETURN FALSE;
 END IF;
 IF row.code_hash<>code_digest THEN
   UPDATE public.auth_otp_challenges SET attempts=attempts+1 WHERE id=challenge;
   INSERT INTO public.auth_security_events(action,mobile_hash) VALUES('OTP_INVALID',row.mobile_hash);
   RETURN FALSE;
 END IF;
 UPDATE public.auth_otp_challenges SET attempts=attempts+1,consumed_at=clock_timestamp(),code_hash=NULL WHERE id=challenge;
 INSERT INTO public.auth_security_events(action,mobile_hash) VALUES('OTP_VERIFIED',row.mobile_hash);
 INSERT INTO public.audit_logs(actor_user_id,action,target_entity,target_id,reason)
 VALUES(subject,'ADMIN_OTP_LOGIN_VERIFIED','users',subject,'LOGIN purpose');
 RETURN TRUE;
END $$;
CREATE FUNCTION km_private.create_admin_session(subject UUID,digest TEXT,ttl_seconds INTEGER)
RETURNS UUID LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE new_id UUID;
BEGIN
 IF ttl_seconds<1 OR ttl_seconds>2592000 OR digest !~ '^[0-9a-f]{64}$' THEN RETURN NULL; END IF;
 PERFORM 1 FROM public.users WHERE id=subject FOR UPDATE;
 IF NOT FOUND OR NOT km_private.admin_active(subject) THEN RETURN NULL; END IF;
 INSERT INTO public.auth_sessions(user_id,refresh_hash,expires_at)
 VALUES(subject,digest,clock_timestamp()+make_interval(secs=>ttl_seconds)) RETURNING id INTO new_id;
 INSERT INTO public.auth_security_events(action,session_id) VALUES('SESSION_CREATED',new_id);
 RETURN new_id;
END $$;

CREATE FUNCTION km_private.issue_admin_reset_otp(mobile TEXT,mobile_digest TEXT,ip_digest TEXT,code_digest TEXT,subject UUID)
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
 IF NOT km_private.admin_active(subject) OR NOT EXISTS(
   SELECT 1 FROM public.users u JOIN km_private.password_credentials c ON c.user_id=u.id
   WHERE u.id=subject AND u.mobile_number=mobile) THEN RETURN NULL; END IF;
 INSERT INTO public.auth_otp_challenges(mobile_number,mobile_hash,code_hash,expires_at,next_request_at,attempts,
   consumed_at,id,purpose,user_id,created_at)
 VALUES(mobile,mobile_digest,code_digest,now_at+interval '120 seconds',now_at+interval '60 seconds',0,
   NULL,challenge,'PASSWORD_RESET',subject,now_at)
 ON CONFLICT(mobile_number) DO UPDATE SET mobile_hash=EXCLUDED.mobile_hash,code_hash=EXCLUDED.code_hash,
   expires_at=EXCLUDED.expires_at,next_request_at=EXCLUDED.next_request_at,attempts=0,consumed_at=NULL,
   id=EXCLUDED.id,purpose='PASSWORD_RESET',user_id=subject,created_at=now_at,intended_partner_role=NULL;
 RETURN challenge;
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
 IF account.role IN ('admin','super_admin') AND NOT km_private.admin_active(subject) THEN RETURN NULL; END IF;
 IF account.role NOT IN ('farmer','shop','consultant','admin','super_admin') THEN RETURN NULL; END IF;
 INSERT INTO public.auth_sessions(user_id,refresh_hash,expires_at)
 VALUES(subject,digest,clock_timestamp()+make_interval(secs=>ttl_seconds)) RETURNING id INTO new_id;
 INSERT INTO public.auth_security_events(action,session_id) VALUES('SESSION_CREATED',new_id);
 RETURN new_id;
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
 IF account.role IN ('admin','super_admin') AND NOT km_private.admin_active(account.id) THEN RETURN FALSE; END IF;
 IF account.role NOT IN ('farmer','shop','consultant','admin','super_admin') THEN RETURN FALSE; END IF;
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
 IF account.role IN ('admin','super_admin') AND NOT km_private.admin_active(subject) THEN RETURN FALSE; END IF;
 IF account.role NOT IN ('farmer','shop','consultant','admin','super_admin') THEN RETURN FALSE; END IF;
 UPDATE km_private.password_credentials SET password_hash=new_hash,updated_at=clock_timestamp()
 WHERE user_id=subject AND password_hash=old_hash;
 IF NOT FOUND THEN RETURN FALSE; END IF;
 UPDATE public.auth_sessions SET revoked_at=clock_timestamp() WHERE user_id=subject AND revoked_at IS NULL;
 INSERT INTO public.auth_security_events(action) VALUES('USER_SESSIONS_REVOKED');
 INSERT INTO public.audit_logs(actor_user_id,action,target_entity,target_id,reason)
 VALUES(subject,'PASSWORD_CHANGED','users',subject,'authenticated password change');
 RETURN TRUE;
END $$;
REVOKE ALL ON FUNCTION km_private.consume_admin_login_otp(UUID,TEXT,UUID,TEXT),
 km_private.create_admin_session(UUID,TEXT,INTEGER),km_private.issue_admin_reset_otp(TEXT,TEXT,TEXT,TEXT,UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION km_private.consume_admin_login_otp(UUID,TEXT,UUID,TEXT),
 km_private.create_admin_session(UUID,TEXT,INTEGER),km_private.issue_admin_reset_otp(TEXT,TEXT,TEXT,TEXT,UUID) TO km_api;
COMMIT;
