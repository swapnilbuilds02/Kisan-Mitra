-- Phase 1 identity foundation. Run as a dedicated migration owner, never km_api.
-- The application login must be granted membership in km_api by the operator.
BEGIN;

CREATE SCHEMA km_private;
CREATE ROLE km_api NOLOGIN;

CREATE TYPE user_role_enum AS ENUM ('farmer', 'shop', 'consultant', 'admin', 'super_admin');
CREATE TYPE account_tier_enum AS ENUM ('free', 'pro');
CREATE TYPE account_state_enum AS ENUM ('active', 'pending_approval', 'suspended', 'expired');

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mobile_number VARCHAR(15) NOT NULL UNIQUE,
    country_code VARCHAR(5) NOT NULL DEFAULT '+91',
    role user_role_enum NOT NULL DEFAULT 'farmer',
    account_tier account_tier_enum NOT NULL DEFAULT 'free',
    account_state account_state_enum NOT NULL DEFAULT 'pending_approval',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT mobile_number_digits CHECK (mobile_number ~ '^[6-9][0-9]{9}$')
);
CREATE INDEX users_role_tier_idx ON users(role, account_tier);

CREATE TABLE farmer_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE RESTRICT,
    farmer_code VARCHAR(30) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    preferred_language VARCHAR(10) NOT NULL DEFAULT 'mr',
    village VARCHAR(100) NOT NULL,
    taluka VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL DEFAULT 'Maharashtra',
    pincode VARCHAR(10),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT farmer_language CHECK (preferred_language IN ('mr', 'en'))
);

CREATE TABLE partner_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE RESTRICT,
    display_name VARCHAR(150) NOT NULL,
    organization_name VARCHAR(150),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id UUID REFERENCES users(id) ON DELETE RESTRICT,
    action VARCHAR(100) NOT NULL,
    target_entity VARCHAR(50) NOT NULL,
    target_id UUID NOT NULL,
    reason TEXT,
    old_state JSONB,
    new_state JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX audit_target_idx ON audit_logs(target_entity, target_id, created_at DESC);

-- No direct table privileges are granted to the runtime role. RLS also applies
-- if a later GRANT is added accidentally. The migration owner retains access
-- for the narrow SECURITY DEFINER lookup and maintenance operations.
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE farmer_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE partner_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON users, farmer_profiles, partner_profiles, audit_logs FROM PUBLIC;

-- The server verifies a signed token before requesting this narrow lookup.
-- Function ownership must stay with the migration owner; grant only EXECUTE.
CREATE FUNCTION km_private.lookup_actor(subject UUID)
RETURNS TABLE (id UUID, role user_role_enum, account_state account_state_enum, account_tier account_tier_enum)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, public
SET row_security = off
AS $$
    SELECT u.id, u.role, u.account_state, u.account_tier
    FROM public.users AS u
    WHERE u.id = subject AND u.is_active = TRUE AND u.is_verified = TRUE
$$;
REVOKE ALL ON FUNCTION km_private.lookup_actor(UUID) FROM PUBLIC;
CREATE FUNCTION km_private.lookup_actor_by_mobile(mobile TEXT)
RETURNS TABLE (id UUID, role user_role_enum, account_state account_state_enum, account_tier account_tier_enum)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, public
SET row_security = off
AS $$
    SELECT u.id, u.role, u.account_state, u.account_tier
    FROM public.users AS u
    WHERE u.mobile_number = mobile AND u.is_active = TRUE AND u.is_verified = TRUE
$$;
REVOKE ALL ON FUNCTION km_private.lookup_actor_by_mobile(TEXT) FROM PUBLIC;
GRANT USAGE ON SCHEMA km_private TO km_api;
GRANT EXECUTE ON FUNCTION km_private.lookup_actor(UUID) TO km_api;
GRANT EXECUTE ON FUNCTION km_private.lookup_actor_by_mobile(TEXT) TO km_api;

COMMIT;
