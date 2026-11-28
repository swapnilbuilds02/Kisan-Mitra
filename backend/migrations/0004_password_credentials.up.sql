BEGIN;
CREATE TABLE km_private.password_credentials (
    user_id UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE RESTRICT,
    password_hash TEXT NOT NULL CHECK (length(password_hash) BETWEEN 40 AND 512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE km_private.password_login_limits (
    scope CHAR(1) NOT NULL CHECK (scope IN ('m', 'i')),
    subject_hash CHAR(64) NOT NULL,
    window_start TIMESTAMPTZ NOT NULL DEFAULT now(),
    attempts INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (scope, subject_hash)
);
CREATE INDEX password_login_limits_window_idx ON km_private.password_login_limits(window_start);
ALTER TABLE km_private.password_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE km_private.password_login_limits ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON km_private.password_credentials, km_private.password_login_limits FROM PUBLIC;

CREATE FUNCTION km_private.password_login_attempt(mobile_digest TEXT, ip_digest TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public, km_private SET row_security = off AS $$
DECLARE allowed BOOLEAN := TRUE;
DECLARE current_attempts INTEGER;
DECLARE current_scope CHAR(1);
DECLARE current_hash CHAR(64);
BEGIN
    IF mobile_digest !~ '^[0-9a-f]{64}$' OR ip_digest !~ '^[0-9a-f]{64}$' THEN
        RETURN FALSE;
    END IF;
    -- Acquire keys in a fixed order to avoid deadlocks across concurrent requests.
    FOR current_scope, current_hash IN
        SELECT 'i'::CHAR(1), ip_digest::CHAR(64)
        UNION ALL SELECT 'm'::CHAR(1), mobile_digest::CHAR(64)
        ORDER BY 1
    LOOP
      INSERT INTO km_private.password_login_limits(scope, subject_hash, attempts)
      VALUES (current_scope, current_hash, 1)
      ON CONFLICT (scope, subject_hash) DO UPDATE
        SET attempts = CASE WHEN password_login_limits.window_start < now() - interval '15 minutes' THEN 1 ELSE password_login_limits.attempts + 1 END,
            window_start = CASE WHEN password_login_limits.window_start < now() - interval '15 minutes' THEN now() ELSE password_login_limits.window_start END
      RETURNING attempts INTO current_attempts;
      IF current_attempts > 5 THEN allowed := FALSE; END IF;
    END LOOP;
    INSERT INTO public.audit_logs(action,target_entity,target_id,reason)
    VALUES ('PASSWORD_LOGIN_ATTEMPT','auth',gen_random_uuid(),'credential attempt');
    RETURN allowed;
END $$;
REVOKE ALL ON FUNCTION km_private.password_login_attempt(TEXT,TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION km_private.password_login_attempt(TEXT,TEXT) TO km_api;

CREATE FUNCTION km_private.read_password_credential(subject UUID)
RETURNS TEXT LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, public, km_private SET row_security = off AS $$
  SELECT password_hash FROM km_private.password_credentials WHERE user_id = subject
$$;
REVOKE ALL ON FUNCTION km_private.read_password_credential(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION km_private.read_password_credential(UUID) TO km_api;

-- Provisioning is migration-owner only. No runtime or public password-setting grant.
CREATE FUNCTION km_private.set_password_credential(subject UUID, new_hash TEXT, replace_existing BOOLEAN DEFAULT FALSE)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public, km_private SET row_security = off AS $$
BEGIN
  IF new_hash !~ '^scrypt\$16384\$8\$1\$' OR length(new_hash) > 512 THEN
    RETURN FALSE;
  END IF;
  IF replace_existing THEN
    UPDATE km_private.password_credentials SET password_hash=new_hash, updated_at=now() WHERE user_id=subject;
    IF NOT FOUND THEN RETURN FALSE; END IF;
  ELSE
    INSERT INTO km_private.password_credentials(user_id,password_hash) VALUES(subject,new_hash);
  END IF;
  INSERT INTO public.audit_logs(actor_user_id,action,target_entity,target_id,reason)
  VALUES(subject,'PASSWORD_CREDENTIAL_CHANGED','users',subject,'internal provisioning');
  RETURN TRUE;
END $$;
REVOKE ALL ON FUNCTION km_private.set_password_credential(UUID,TEXT,BOOLEAN) FROM PUBLIC;
COMMIT;
