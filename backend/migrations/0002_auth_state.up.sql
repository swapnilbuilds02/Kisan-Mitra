-- Apply after 0001, using the migration owner on an isolated database first.
BEGIN;

CREATE TABLE auth_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    refresh_hash CHAR(64) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    rotated_at TIMESTAMPTZ,
    CONSTRAINT auth_session_hash_hex CHECK (refresh_hash ~ '^[0-9a-f]{64}$')
);
CREATE INDEX auth_sessions_user_active_idx ON auth_sessions(user_id, expires_at) WHERE revoked_at IS NULL;

CREATE TABLE auth_refresh_history (
    session_id UUID NOT NULL REFERENCES auth_sessions(id) ON DELETE CASCADE,
    token_hash CHAR(64) NOT NULL,
    consumed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, token_hash),
    CONSTRAINT auth_refresh_hash_hex CHECK (token_hash ~ '^[0-9a-f]{64}$')
);

CREATE TABLE auth_otp_challenges (
    mobile_number VARCHAR(15) PRIMARY KEY,
    mobile_hash CHAR(64) NOT NULL,
    code_hash CHAR(64),
    expires_at TIMESTAMPTZ NOT NULL,
    next_request_at TIMESTAMPTZ NOT NULL,
    attempts SMALLINT NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 5),
    consumed_at TIMESTAMPTZ,
    CONSTRAINT otp_code_hash_hex CHECK (code_hash IS NULL OR code_hash ~ '^[0-9a-f]{64}$')
);

CREATE TABLE auth_otp_requests (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mobile_hash CHAR(64) NOT NULL,
    ip_hash CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX otp_requests_mobile_time_idx ON auth_otp_requests(mobile_hash, created_at DESC);
CREATE INDEX otp_requests_ip_time_idx ON auth_otp_requests(ip_hash, created_at DESC);

CREATE TABLE auth_security_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    action VARCHAR(40) NOT NULL,
    mobile_hash CHAR(64),
    ip_hash CHAR(64),
    session_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT auth_event_action CHECK (action IN (
        'OTP_ISSUED', 'OTP_LIMITED', 'OTP_INVALID', 'OTP_VERIFIED',
        'SESSION_CREATED', 'SESSION_ROTATED', 'REFRESH_REUSED',
        'SESSION_REVOKED', 'USER_SESSIONS_REVOKED'
    ))
);
CREATE INDEX auth_events_time_idx ON auth_security_events(created_at DESC);

ALTER TABLE auth_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_refresh_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_otp_challenges ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_otp_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_security_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON auth_sessions, auth_refresh_history, auth_otp_challenges, auth_otp_requests, auth_security_events FROM PUBLIC;

CREATE FUNCTION km_private.create_session(subject UUID, digest TEXT, ttl_seconds INTEGER)
RETURNS UUID LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
DECLARE new_id UUID;
BEGIN
    IF ttl_seconds < 1 OR ttl_seconds > 2592000 OR digest !~ '^[0-9a-f]{64}$' THEN
        RAISE EXCEPTION 'Invalid session input';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.users
        WHERE id = subject AND is_active AND is_verified
          AND role = 'farmer' AND account_state = 'active'
    ) THEN
        RAISE EXCEPTION 'Inactive identity';
    END IF;
    INSERT INTO public.auth_sessions(user_id, refresh_hash, expires_at)
    VALUES (subject, digest, clock_timestamp() + make_interval(secs => ttl_seconds))
    RETURNING id INTO new_id;
    INSERT INTO public.auth_security_events(action, session_id) VALUES ('SESSION_CREATED', new_id);
    RETURN new_id;
END $$;

CREATE FUNCTION km_private.session_active(subject UUID, session UUID)
RETURNS BOOLEAN LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.auth_sessions
        WHERE id = session AND user_id = subject AND revoked_at IS NULL
          AND expires_at > now()
    )
$$;

CREATE FUNCTION km_private.rotate_session(session UUID, old_digest TEXT, new_digest TEXT, ttl_seconds INTEGER)
RETURNS TABLE (result TEXT, subject UUID) LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
DECLARE current_row public.auth_sessions%ROWTYPE;
BEGIN
    IF ttl_seconds < 1 OR ttl_seconds > 2592000 OR new_digest !~ '^[0-9a-f]{64}$' THEN
        RETURN QUERY SELECT 'invalid'::TEXT, NULL::UUID;
        RETURN;
    END IF;
    SELECT * INTO current_row FROM public.auth_sessions WHERE id = session FOR UPDATE;
    IF NOT FOUND THEN
        RETURN QUERY SELECT 'invalid'::TEXT, NULL::UUID;
        RETURN;
    END IF;
    IF EXISTS (SELECT 1 FROM public.auth_refresh_history WHERE session_id = session AND token_hash = old_digest) THEN
        UPDATE public.auth_sessions SET revoked_at = clock_timestamp()
        WHERE user_id = current_row.user_id AND revoked_at IS NULL;
        INSERT INTO public.auth_security_events(action, session_id) VALUES ('REFRESH_REUSED', session);
        RETURN QUERY SELECT 'reused'::TEXT, current_row.user_id;
        RETURN;
    END IF;
    IF current_row.revoked_at IS NOT NULL OR current_row.expires_at <= clock_timestamp()
       OR current_row.refresh_hash <> old_digest THEN
        RETURN QUERY SELECT 'invalid'::TEXT, NULL::UUID;
        RETURN;
    END IF;
    INSERT INTO public.auth_refresh_history(session_id, token_hash) VALUES (session, old_digest);
    UPDATE public.auth_sessions SET refresh_hash = new_digest,
        expires_at = clock_timestamp() + make_interval(secs => ttl_seconds),
        rotated_at = clock_timestamp() WHERE id = session;
    INSERT INTO public.auth_security_events(action, session_id) VALUES ('SESSION_ROTATED', session);
    RETURN QUERY SELECT 'rotated'::TEXT, current_row.user_id;
END $$;

CREATE FUNCTION km_private.revoke_session(session UUID)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
BEGIN
    UPDATE public.auth_sessions SET revoked_at = clock_timestamp()
    WHERE id = session AND revoked_at IS NULL;
    INSERT INTO public.auth_security_events(action, session_id) VALUES ('SESSION_REVOKED', session);
END $$;

CREATE FUNCTION km_private.revoke_user_sessions(subject UUID)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
BEGIN
    UPDATE public.auth_sessions SET revoked_at = clock_timestamp()
    WHERE user_id = subject AND revoked_at IS NULL;
    INSERT INTO public.auth_security_events(action) VALUES ('USER_SESSIONS_REVOKED');
END $$;

CREATE FUNCTION km_private.issue_otp(mobile TEXT, mobile_digest TEXT, ip_digest TEXT, code_digest TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
DECLARE m_lock BIGINT := hashtextextended('m:' || mobile_digest, 0);
DECLARE i_lock BIGINT := hashtextextended('i:' || ip_digest, 0);
DECLARE now_at TIMESTAMPTZ := clock_timestamp();
BEGIN
    IF mobile !~ '^[0-9]{10}$' OR mobile_digest !~ '^[0-9a-f]{64}$'
       OR ip_digest !~ '^[0-9a-f]{64}$' OR code_digest !~ '^[0-9a-f]{64}$' THEN
        RAISE EXCEPTION 'Invalid OTP input';
    END IF;
    PERFORM pg_advisory_xact_lock(LEAST(m_lock, i_lock));
    IF m_lock <> i_lock THEN
        PERFORM pg_advisory_xact_lock(GREATEST(m_lock, i_lock));
    END IF;
    IF (SELECT count(*) FROM public.auth_otp_requests WHERE mobile_hash = mobile_digest AND created_at > now_at - interval '1 hour') >= 3
       OR (SELECT count(*) FROM public.auth_otp_requests WHERE ip_hash = ip_digest AND created_at > now_at - interval '1 hour') >= 3
       OR EXISTS (SELECT 1 FROM public.auth_otp_challenges WHERE mobile_number = mobile AND next_request_at > now_at) THEN
        INSERT INTO public.auth_security_events(action, mobile_hash, ip_hash)
        VALUES ('OTP_LIMITED', mobile_digest, ip_digest);
        RETURN FALSE;
    END IF;
    INSERT INTO public.auth_otp_requests(mobile_hash, ip_hash) VALUES (mobile_digest, ip_digest);
    INSERT INTO public.auth_otp_challenges(mobile_number, mobile_hash, code_hash, expires_at, next_request_at, attempts, consumed_at)
    VALUES (mobile, mobile_digest, code_digest, now_at + interval '120 seconds', now_at + interval '60 seconds', 0, NULL)
    ON CONFLICT (mobile_number) DO UPDATE SET mobile_hash = EXCLUDED.mobile_hash,
        code_hash = EXCLUDED.code_hash, expires_at = EXCLUDED.expires_at,
        next_request_at = EXCLUDED.next_request_at, attempts = 0, consumed_at = NULL;
    INSERT INTO public.auth_security_events(action, mobile_hash, ip_hash)
    VALUES ('OTP_ISSUED', mobile_digest, ip_digest);
    RETURN TRUE;
END $$;

CREATE FUNCTION km_private.consume_otp(mobile TEXT, mobile_digest TEXT, code_digest TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
DECLARE challenge public.auth_otp_challenges%ROWTYPE;
BEGIN
    SELECT * INTO challenge FROM public.auth_otp_challenges
    WHERE mobile_number = mobile FOR UPDATE;
    IF NOT FOUND OR challenge.consumed_at IS NOT NULL
       OR challenge.expires_at <= clock_timestamp() OR challenge.attempts >= 5 THEN
        INSERT INTO public.auth_security_events(action, mobile_hash) VALUES ('OTP_INVALID', mobile_digest);
        RETURN FALSE;
    END IF;
    IF challenge.code_hash = code_digest THEN
        UPDATE public.auth_otp_challenges SET attempts = attempts + 1,
            consumed_at = clock_timestamp(), code_hash = NULL WHERE mobile_number = mobile;
        INSERT INTO public.auth_security_events(action, mobile_hash) VALUES ('OTP_VERIFIED', mobile_digest);
        RETURN TRUE;
    END IF;
    UPDATE public.auth_otp_challenges SET attempts = attempts + 1 WHERE mobile_number = mobile;
    INSERT INTO public.auth_security_events(action, mobile_hash) VALUES ('OTP_INVALID', mobile_digest);
    RETURN FALSE;
END $$;

REVOKE ALL ON FUNCTION km_private.create_session(UUID, TEXT, INTEGER),
    km_private.session_active(UUID, UUID), km_private.rotate_session(UUID, TEXT, TEXT, INTEGER),
    km_private.revoke_session(UUID), km_private.revoke_user_sessions(UUID),
    km_private.issue_otp(TEXT, TEXT, TEXT, TEXT), km_private.consume_otp(TEXT, TEXT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION km_private.create_session(UUID, TEXT, INTEGER),
    km_private.session_active(UUID, UUID), km_private.rotate_session(UUID, TEXT, TEXT, INTEGER),
    km_private.revoke_session(UUID), km_private.revoke_user_sessions(UUID),
    km_private.issue_otp(TEXT, TEXT, TEXT, TEXT), km_private.consume_otp(TEXT, TEXT, TEXT) TO km_api;

COMMIT;
