BEGIN;
ALTER TABLE public.auth_otp_challenges ADD COLUMN id UUID NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE public.auth_otp_challenges ADD COLUMN purpose TEXT NOT NULL DEFAULT 'LOGIN' CHECK (purpose IN ('REGISTRATION','LOGIN','ACCOUNT_CLAIM','PASSWORD_RESET'));
ALTER TABLE public.auth_otp_challenges ADD COLUMN user_id UUID REFERENCES public.users(id) ON DELETE RESTRICT;
ALTER TABLE public.auth_otp_challenges ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT now();
CREATE UNIQUE INDEX auth_otp_challenge_id_idx ON public.auth_otp_challenges(id);
-- Old unlabelled codes cannot safely be assigned a purpose.
UPDATE public.auth_otp_challenges SET code_hash=NULL, consumed_at=clock_timestamp();
CREATE TABLE km_private.password_reset_authorizations (
    token_hash CHAR(64) PRIMARY KEY CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX password_reset_authorizations_user_idx ON km_private.password_reset_authorizations(user_id,expires_at);
ALTER TABLE km_private.password_reset_authorizations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON km_private.password_reset_authorizations FROM PUBLIC;

-- Preserve the legacy Farmer route while binding its challenges to LOGIN.
CREATE OR REPLACE FUNCTION km_private.issue_otp(mobile TEXT, mobile_digest TEXT, ip_digest TEXT, code_digest TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
DECLARE now_at TIMESTAMPTZ := clock_timestamp();
BEGIN
  IF mobile !~ '^[6-9][0-9]{9}$' OR mobile_digest !~ '^[0-9a-f]{64}$'
      OR ip_digest !~ '^[0-9a-f]{64}$' OR code_digest !~ '^[0-9a-f]{64}$' THEN RETURN FALSE; END IF;
  PERFORM pg_advisory_xact_lock(hashtextextended('otp:' || mobile, 0));
  IF (SELECT count(*) FROM public.auth_otp_requests WHERE mobile_hash=mobile_digest AND created_at>now_at-interval '1 hour')>=3
    OR (SELECT count(*) FROM public.auth_otp_requests WHERE ip_hash=ip_digest AND created_at>now_at-interval '1 hour')>=3
    OR EXISTS(SELECT 1 FROM public.auth_otp_challenges WHERE mobile_number=mobile AND next_request_at>now_at) THEN
    INSERT INTO public.auth_security_events(action,mobile_hash,ip_hash) VALUES('OTP_LIMITED',mobile_digest,ip_digest);
    RETURN FALSE;
  END IF;
  INSERT INTO public.auth_otp_requests(mobile_hash,ip_hash) VALUES(mobile_digest,ip_digest);
  INSERT INTO public.auth_otp_challenges(mobile_number,mobile_hash,code_hash,expires_at,next_request_at,attempts,consumed_at,id,purpose,user_id,created_at)
  VALUES(mobile,mobile_digest,code_digest,now_at+interval '120 seconds',now_at+interval '60 seconds',0,NULL,gen_random_uuid(),'LOGIN',NULL,now_at)
  ON CONFLICT(mobile_number) DO UPDATE SET mobile_hash=EXCLUDED.mobile_hash,code_hash=EXCLUDED.code_hash,
    expires_at=EXCLUDED.expires_at,next_request_at=EXCLUDED.next_request_at,attempts=0,consumed_at=NULL,
    id=EXCLUDED.id,purpose='LOGIN',user_id=NULL,created_at=now_at;
  INSERT INTO public.auth_security_events(action,mobile_hash,ip_hash) VALUES('OTP_ISSUED',mobile_digest,ip_digest);
  RETURN TRUE;
END $$;
CREATE OR REPLACE FUNCTION km_private.consume_otp(mobile TEXT,mobile_digest TEXT,code_digest TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
DECLARE row public.auth_otp_challenges%ROWTYPE;
BEGIN
  SELECT * INTO row FROM public.auth_otp_challenges WHERE mobile_number=mobile FOR UPDATE;
  IF NOT FOUND OR row.purpose<>'LOGIN' OR row.consumed_at IS NOT NULL OR row.expires_at<=clock_timestamp() OR row.attempts>=5 THEN
    INSERT INTO public.auth_security_events(action,mobile_hash) VALUES('OTP_INVALID',mobile_digest); RETURN FALSE;
  END IF;
  IF row.code_hash=code_digest THEN
    UPDATE public.auth_otp_challenges SET attempts=attempts+1,consumed_at=clock_timestamp(),code_hash=NULL WHERE id=row.id;
    INSERT INTO public.auth_security_events(action,mobile_hash) VALUES('OTP_VERIFIED',mobile_digest); RETURN TRUE;
  END IF;
  UPDATE public.auth_otp_challenges SET attempts=attempts+1 WHERE id=row.id;
  INSERT INTO public.auth_security_events(action,mobile_hash) VALUES('OTP_INVALID',mobile_digest); RETURN FALSE;
END $$;

CREATE FUNCTION km_private.issue_purpose_otp(mobile TEXT,mobile_digest TEXT,ip_digest TEXT,code_digest TEXT,otp_purpose TEXT,subject UUID)
RETURNS UUID LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public SET row_security=off AS $$
DECLARE now_at TIMESTAMPTZ:=clock_timestamp(); challenge UUID:=gen_random_uuid();
BEGIN
  IF mobile !~ '^[6-9][0-9]{9}$' OR mobile_digest !~ '^[0-9a-f]{64}$' OR ip_digest !~ '^[0-9a-f]{64}$'
     OR code_digest !~ '^[0-9a-f]{64}$' OR otp_purpose NOT IN ('REGISTRATION','LOGIN','ACCOUNT_CLAIM','PASSWORD_RESET') THEN RETURN NULL; END IF;
  PERFORM pg_advisory_xact_lock(hashtextextended('otp:'||mobile,0));
  IF (SELECT count(*) FROM public.auth_otp_requests WHERE mobile_hash=mobile_digest AND created_at>now_at-interval '1 hour')>=3
     OR (SELECT count(*) FROM public.auth_otp_requests WHERE ip_hash=ip_digest AND created_at>now_at-interval '1 hour')>=3
     OR EXISTS(SELECT 1 FROM public.auth_otp_challenges WHERE mobile_number=mobile AND next_request_at>now_at) THEN
    INSERT INTO public.auth_security_events(action,mobile_hash,ip_hash) VALUES('OTP_LIMITED',mobile_digest,ip_digest); RETURN NULL;
  END IF;
  INSERT INTO public.auth_otp_requests(mobile_hash,ip_hash) VALUES(mobile_digest,ip_digest);
  IF otp_purpose='PASSWORD_RESET' AND NOT EXISTS(
    SELECT 1 FROM public.users u JOIN km_private.password_credentials c ON c.user_id=u.id
    WHERE u.id=subject AND u.mobile_number=mobile AND u.is_verified AND u.is_active AND u.account_state='active' AND u.role='farmer') THEN RETURN NULL; END IF;
  INSERT INTO public.auth_otp_challenges(mobile_number,mobile_hash,code_hash,expires_at,next_request_at,attempts,consumed_at,id,purpose,user_id,created_at)
  VALUES(mobile,mobile_digest,code_digest,now_at+interval '120 seconds',now_at+interval '60 seconds',0,NULL,challenge,otp_purpose,subject,now_at)
  ON CONFLICT(mobile_number) DO UPDATE SET mobile_hash=EXCLUDED.mobile_hash,code_hash=EXCLUDED.code_hash,
    expires_at=EXCLUDED.expires_at,next_request_at=EXCLUDED.next_request_at,attempts=0,consumed_at=NULL,
    id=EXCLUDED.id,purpose=EXCLUDED.purpose,user_id=EXCLUDED.user_id,created_at=now_at;
  INSERT INTO public.auth_security_events(action,mobile_hash,ip_hash) VALUES('OTP_ISSUED',mobile_digest,ip_digest);
  RETURN challenge;
END $$;
CREATE FUNCTION km_private.consume_reset_otp(challenge UUID,code_digest TEXT,authorization_digest TEXT)
RETURNS UUID LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public SET row_security=off AS $$
DECLARE row public.auth_otp_challenges%ROWTYPE;
BEGIN
  IF code_digest !~ '^[0-9a-f]{64}$' OR authorization_digest !~ '^[0-9a-f]{64}$' THEN RETURN NULL; END IF;
  SELECT * INTO row FROM public.auth_otp_challenges WHERE id=challenge FOR UPDATE;
  IF NOT FOUND OR row.purpose<>'PASSWORD_RESET' OR row.user_id IS NULL OR row.consumed_at IS NOT NULL
     OR row.expires_at<=clock_timestamp() OR row.attempts>=5 THEN RETURN NULL; END IF;
  IF row.code_hash<>code_digest THEN
    UPDATE public.auth_otp_challenges SET attempts=attempts+1 WHERE id=challenge;
    INSERT INTO public.auth_security_events(action,mobile_hash) VALUES('OTP_INVALID',row.mobile_hash); RETURN NULL;
  END IF;
  UPDATE public.auth_otp_challenges SET attempts=attempts+1,consumed_at=clock_timestamp(),code_hash=NULL WHERE id=challenge;
  INSERT INTO km_private.password_reset_authorizations(token_hash,user_id,expires_at)
    VALUES(authorization_digest,row.user_id,clock_timestamp()+interval '10 minutes');
  INSERT INTO public.auth_security_events(action,mobile_hash) VALUES('OTP_VERIFIED',row.mobile_hash);
  RETURN row.user_id;
END $$;
CREATE FUNCTION km_private.complete_password_reset(authorization_digest TEXT,new_hash TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE authrow km_private.password_reset_authorizations%ROWTYPE;
BEGIN
  IF new_hash !~ '^scrypt\$16384\$8\$1\$' OR length(new_hash)>512 THEN RETURN FALSE; END IF;
  SELECT * INTO authrow FROM km_private.password_reset_authorizations WHERE token_hash=authorization_digest FOR UPDATE;
  IF NOT FOUND OR authrow.consumed_at IS NOT NULL OR authrow.expires_at<=clock_timestamp() THEN RETURN FALSE; END IF;
  PERFORM 1 FROM public.users WHERE id=authrow.user_id AND role='farmer' AND is_verified AND is_active AND account_state='active' FOR UPDATE;
  IF NOT FOUND THEN RETURN FALSE; END IF;
  IF EXISTS(SELECT 1 FROM km_private.password_reset_authorizations WHERE token_hash=authorization_digest AND consumed_at IS NOT NULL) THEN RETURN FALSE; END IF;
  UPDATE km_private.password_credentials SET password_hash=new_hash,updated_at=clock_timestamp() WHERE user_id=authrow.user_id;
  IF NOT FOUND THEN RETURN FALSE; END IF;
  UPDATE km_private.password_reset_authorizations SET consumed_at=clock_timestamp() WHERE user_id=authrow.user_id AND consumed_at IS NULL;
  UPDATE public.auth_sessions SET revoked_at=clock_timestamp() WHERE user_id=authrow.user_id AND revoked_at IS NULL;
  INSERT INTO public.auth_security_events(action) VALUES('USER_SESSIONS_REVOKED');
  INSERT INTO public.audit_logs(actor_user_id,action,target_entity,target_id,reason)
    VALUES(authrow.user_id,'PASSWORD_RESET','users',authrow.user_id,'OTP authorized');
  RETURN TRUE;
END $$;
CREATE FUNCTION km_private.create_password_session(subject UUID,digest TEXT,ttl_seconds INTEGER,credential_hash TEXT)
RETURNS UUID LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE new_id UUID;
BEGIN
  IF ttl_seconds<1 OR ttl_seconds>2592000 OR digest !~ '^[0-9a-f]{64}$' THEN RETURN NULL; END IF;
  PERFORM 1 FROM public.users WHERE id=subject AND is_active AND is_verified AND account_state='active' AND role='farmer' FOR UPDATE;
  IF NOT FOUND OR NOT EXISTS(SELECT 1 FROM km_private.password_credentials WHERE user_id=subject AND password_hash=credential_hash) THEN RETURN NULL; END IF;
  INSERT INTO public.auth_sessions(user_id,refresh_hash,expires_at)
    VALUES(subject,digest,clock_timestamp()+make_interval(secs=>ttl_seconds)) RETURNING id INTO new_id;
  INSERT INTO public.auth_security_events(action,session_id) VALUES('SESSION_CREATED',new_id);
  RETURN new_id;
END $$;
CREATE FUNCTION km_private.change_password_credential(subject UUID,old_hash TEXT,new_hash TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
BEGIN
  IF new_hash !~ '^scrypt\$16384\$8\$1\$' OR length(new_hash)>512 THEN RETURN FALSE; END IF;
  PERFORM 1 FROM public.users WHERE id=subject AND is_active AND is_verified AND account_state='active' AND role='farmer' FOR UPDATE;
  IF NOT FOUND THEN RETURN FALSE; END IF;
  UPDATE km_private.password_credentials SET password_hash=new_hash,updated_at=clock_timestamp()
    WHERE user_id=subject AND password_hash=old_hash;
  IF NOT FOUND THEN RETURN FALSE; END IF;
  UPDATE public.auth_sessions SET revoked_at=clock_timestamp() WHERE user_id=subject AND revoked_at IS NULL;
  INSERT INTO public.auth_security_events(action) VALUES('USER_SESSIONS_REVOKED');
  INSERT INTO public.audit_logs(actor_user_id,action,target_entity,target_id,reason)
    VALUES(subject,'PASSWORD_CHANGED','users',subject,'authenticated password change');
  RETURN TRUE;
END $$;
REVOKE ALL ON FUNCTION km_private.issue_purpose_otp(TEXT,TEXT,TEXT,TEXT,TEXT,UUID),
 km_private.consume_reset_otp(UUID,TEXT,TEXT),km_private.complete_password_reset(TEXT,TEXT),
 km_private.create_password_session(UUID,TEXT,INTEGER,TEXT),km_private.change_password_credential(UUID,TEXT,TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION km_private.issue_purpose_otp(TEXT,TEXT,TEXT,TEXT,TEXT,UUID),
 km_private.consume_reset_otp(UUID,TEXT,TEXT),km_private.complete_password_reset(TEXT,TEXT),
 km_private.create_password_session(UUID,TEXT,INTEGER,TEXT),km_private.change_password_credential(UUID,TEXT,TEXT) TO km_api;
COMMIT;
