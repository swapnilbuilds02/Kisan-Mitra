-- Apply after 0001 and 0002. No partner relationship is created here.
BEGIN;

CREATE FUNCTION km_private.prepare_farmer(mobile TEXT, operator_id UUID, correction_reason TEXT)
RETURNS UUID LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
DECLARE existing public.users%ROWTYPE;
DECLARE new_id UUID;
BEGIN
    IF mobile !~ '^[6-9][0-9]{9}$' OR length(trim(coalesce(correction_reason, ''))) < 5 THEN
        RAISE EXCEPTION 'Invalid farmer preparation request';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.users WHERE id = operator_id AND is_active AND is_verified
          AND account_state = 'active' AND role IN ('admin', 'super_admin')
    ) THEN
        RAISE EXCEPTION 'Unauthorized operator';
    END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended('farmer:' || mobile, 0));
    SELECT * INTO existing FROM public.users WHERE mobile_number = mobile FOR UPDATE;
    IF FOUND THEN
        IF existing.role <> 'farmer' THEN
            RAISE EXCEPTION 'Mobile belongs to another role';
        END IF;
        -- Never reset or reassign an existing identity in this path.
        INSERT INTO public.audit_logs(actor_user_id, action, target_entity, target_id, reason)
        VALUES (operator_id, 'FARMER_PREPARE_EXISTING', 'users', existing.id, correction_reason);
        RETURN existing.id;
    END IF;
    INSERT INTO public.users(mobile_number, role, account_state, is_verified)
    VALUES (mobile, 'farmer', 'pending_approval', FALSE) RETURNING id INTO new_id;
    INSERT INTO public.audit_logs(actor_user_id, action, target_entity, target_id, reason, new_state)
    VALUES (operator_id, 'FARMER_PREPARED', 'users', new_id, correction_reason,
        jsonb_build_object('role', 'farmer', 'is_verified', FALSE));
    RETURN new_id;
END $$;

CREATE FUNCTION km_private.claim_farmer(mobile TEXT)
RETURNS TABLE (id UUID, role user_role_enum, account_state account_state_enum, account_tier account_tier_enum)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
DECLARE existing public.users%ROWTYPE;
DECLARE new_id UUID;
BEGIN
    IF mobile !~ '^[6-9][0-9]{9}$' THEN
        RAISE EXCEPTION 'Invalid mobile';
    END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended('farmer:' || mobile, 0));
    SELECT * INTO existing FROM public.users AS u WHERE u.mobile_number = mobile FOR UPDATE;
    IF NOT FOUND THEN
        INSERT INTO public.users(mobile_number, role, account_state, is_verified)
        VALUES (mobile, 'farmer', 'active', TRUE) RETURNING users.id INTO new_id;
        INSERT INTO public.audit_logs(actor_user_id, action, target_entity, target_id, new_state)
        VALUES (new_id, 'FARMER_SELF_REGISTERED', 'users', new_id,
            jsonb_build_object('role', 'farmer', 'is_verified', TRUE));
    ELSE
        IF existing.role <> 'farmer' OR NOT existing.is_active OR existing.account_state IN ('suspended', 'expired') THEN
            RETURN;
        END IF;
        new_id := existing.id;
        IF NOT existing.is_verified THEN
            UPDATE public.users SET is_verified = TRUE, account_state = 'active', updated_at = clock_timestamp()
            WHERE users.id = new_id AND is_verified = FALSE;
            INSERT INTO public.audit_logs(actor_user_id, action, target_entity, target_id, old_state, new_state)
            VALUES (new_id, 'FARMER_ACCOUNT_CLAIMED', 'users', new_id,
                jsonb_build_object('is_verified', FALSE), jsonb_build_object('is_verified', TRUE));
        END IF;
    END IF;
    RETURN QUERY SELECT u.id, u.role, u.account_state, u.account_tier
    FROM public.users AS u WHERE u.id = new_id AND u.is_active AND u.is_verified AND u.role = 'farmer';
END $$;

REVOKE ALL ON FUNCTION km_private.prepare_farmer(TEXT, UUID, TEXT), km_private.claim_farmer(TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION km_private.prepare_farmer(TEXT, UUID, TEXT), km_private.claim_farmer(TEXT) TO km_api;

COMMIT;
