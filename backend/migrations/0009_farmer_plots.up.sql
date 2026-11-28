-- Stage 2A additive plot storage. Apply only after 0008, as migration owner.
BEGIN;
CREATE TABLE public.farmer_plots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  farmer_user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
  plot_name VARCHAR(120) NOT NULL CHECK(length(btrim(plot_name)) >= 2),
  crop_type VARCHAR(40) NOT NULL CHECK(crop_type ~ '^[a-z][a-z0-9_]{1,39}$'),
  grape_variety VARCHAR(120),
  area NUMERIC(12,3) NOT NULL CHECK(area > 0 AND area <= 1000000),
  area_unit VARCHAR(12) NOT NULL CHECK(area_unit IN ('acre','hectare','sq_m')),
  village VARCHAR(100) NOT NULL CHECK(length(btrim(village)) > 0),
  taluka VARCHAR(100) NOT NULL CHECK(length(btrim(taluka)) > 0),
  district VARCHAR(100) NOT NULL CHECK(length(btrim(district)) > 0),
  state VARCHAR(100) NOT NULL CHECK(length(btrim(state)) > 0),
  latitude NUMERIC(9,6) CHECK(latitude BETWEEN -90 AND 90),
  longitude NUMERIC(9,6) CHECK(longitude BETWEEN -180 AND 180),
  location_permission_at TIMESTAMPTZ,
  pruning_date DATE,
  current_crop_stage VARCHAR(40) NOT NULL DEFAULT 'not_set'
    CHECK(current_crop_stage ~ '^[a-z][a-z0-9_]{1,39}$'),
  preferred_language VARCHAR(2) NOT NULL DEFAULT 'mr' CHECK(preferred_language IN ('mr','en')),
  status VARCHAR(8) NOT NULL DEFAULT 'active' CHECK(status IN ('active','archived')),
  is_selected BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  CONSTRAINT plot_coordinates_with_permission CHECK (
    (latitude IS NULL AND longitude IS NULL AND location_permission_at IS NULL)
    OR (latitude IS NOT NULL AND longitude IS NOT NULL AND location_permission_at IS NOT NULL)),
  CONSTRAINT archived_plot_not_selected CHECK(status='active' OR NOT is_selected)
);
CREATE INDEX farmer_plots_owner_created_idx ON public.farmer_plots(farmer_user_id,created_at DESC);
CREATE UNIQUE INDEX farmer_plots_one_selected_idx ON public.farmer_plots(farmer_user_id)
  WHERE is_selected AND status='active';
ALTER TABLE public.farmer_plots ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.farmer_plots FROM PUBLIC;

CREATE FUNCTION km_private.create_farmer_plot(
  subject UUID, name TEXT, crop TEXT, variety TEXT, plot_area NUMERIC, unit TEXT,
  plot_village TEXT, plot_taluka TEXT, plot_district TEXT, plot_state TEXT,
  lat NUMERIC, lon NUMERIC, location_ok BOOLEAN, pruning DATE, stage TEXT, language_code TEXT)
RETURNS UUID LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE result UUID; selected_now BOOLEAN;
BEGIN
  PERFORM 1 FROM public.users WHERE id=subject AND role='farmer' AND is_active
    AND is_verified AND account_state='active' FOR UPDATE;
  IF NOT FOUND OR location_ok IS NULL OR (lat IS NULL)<>(lon IS NULL)
     OR (lat IS NOT NULL AND NOT location_ok) OR (pruning IS NOT NULL AND pruning>CURRENT_DATE) THEN
    RETURN NULL;
  END IF;
  SELECT NOT EXISTS(SELECT 1 FROM public.farmer_plots WHERE farmer_user_id=subject
    AND status='active' AND is_selected) INTO selected_now;
  INSERT INTO public.farmer_plots(farmer_user_id,plot_name,crop_type,grape_variety,area,area_unit,
    village,taluka,district,state,latitude,longitude,location_permission_at,pruning_date,
    current_crop_stage,preferred_language,is_selected)
  VALUES(subject,btrim(name),crop,NULLIF(btrim(variety),''),plot_area,unit,btrim(plot_village),
    btrim(plot_taluka),btrim(plot_district),btrim(plot_state),lat,lon,
    CASE WHEN lat IS NOT NULL THEN clock_timestamp() ELSE NULL END,pruning,stage,language_code,selected_now)
  RETURNING id INTO result;
  INSERT INTO public.audit_logs(actor_user_id,action,target_entity,target_id,new_state)
    VALUES(subject,'PLOT_CREATED','farmer_plots',result,jsonb_build_object('crop_type',crop));
  RETURN result;
END $$;

CREATE FUNCTION km_private.farmer_plots_for(subject UUID)
RETURNS SETOF public.farmer_plots LANGUAGE sql STABLE SECURITY DEFINER
SET search_path=pg_catalog,public SET row_security=off AS $$
  SELECT * FROM public.farmer_plots WHERE farmer_user_id=subject
  ORDER BY is_selected DESC,created_at DESC,id
$$;
CREATE FUNCTION km_private.farmer_plot_for(subject UUID, plot_id UUID)
RETURNS SETOF public.farmer_plots LANGUAGE sql STABLE SECURITY DEFINER
SET search_path=pg_catalog,public SET row_security=off AS $$
  SELECT * FROM public.farmer_plots WHERE farmer_user_id=subject AND id=plot_id
$$;

CREATE FUNCTION km_private.update_farmer_plot(
  subject UUID, plot_id UUID, name TEXT, crop TEXT, variety TEXT, plot_area NUMERIC, unit TEXT,
  plot_village TEXT, plot_taluka TEXT, plot_district TEXT, plot_state TEXT,
  lat NUMERIC, lon NUMERIC, location_ok BOOLEAN, pruning DATE, stage TEXT, language_code TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE old_row public.farmer_plots%ROWTYPE;
BEGIN
  PERFORM 1 FROM public.users WHERE id=subject AND role='farmer' AND is_active
    AND is_verified AND account_state='active' FOR UPDATE;
  IF NOT FOUND OR location_ok IS NULL OR (lat IS NULL)<>(lon IS NULL)
     OR (lat IS NOT NULL AND NOT location_ok) OR (pruning IS NOT NULL AND pruning>CURRENT_DATE) THEN
    RETURN FALSE;
  END IF;
  SELECT * INTO old_row FROM public.farmer_plots
    WHERE id=plot_id AND farmer_user_id=subject AND status='active' FOR UPDATE;
  IF NOT FOUND THEN RETURN FALSE; END IF;
  UPDATE public.farmer_plots SET plot_name=btrim(name),crop_type=crop,grape_variety=NULLIF(btrim(variety),''),
    area=plot_area,area_unit=unit,village=btrim(plot_village),taluka=btrim(plot_taluka),
    district=btrim(plot_district),state=btrim(plot_state),latitude=lat,longitude=lon,
    location_permission_at=CASE WHEN lat IS NULL THEN NULL
      WHEN old_row.latitude=lat AND old_row.longitude=lon THEN old_row.location_permission_at
      ELSE clock_timestamp() END,
    pruning_date=pruning,current_crop_stage=stage,preferred_language=language_code,
    updated_at=clock_timestamp() WHERE id=plot_id;
  INSERT INTO public.audit_logs(actor_user_id,action,target_entity,target_id,old_state,new_state)
    VALUES(subject,'PLOT_UPDATED','farmer_plots',plot_id,
      jsonb_build_object('crop_type',old_row.crop_type,'stage',old_row.current_crop_stage),
      jsonb_build_object('crop_type',crop,'stage',stage));
  RETURN TRUE;
END $$;

CREATE FUNCTION km_private.archive_farmer_plot(subject UUID, plot_id UUID)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
DECLARE was_selected BOOLEAN;
BEGIN
  PERFORM 1 FROM public.users WHERE id=subject AND role='farmer' AND is_active
    AND is_verified AND account_state='active' FOR UPDATE;
  IF NOT FOUND THEN RETURN FALSE; END IF;
  SELECT is_selected INTO was_selected FROM public.farmer_plots
    WHERE id=plot_id AND farmer_user_id=subject AND status='active' FOR UPDATE;
  IF NOT FOUND THEN RETURN FALSE; END IF;
  UPDATE public.farmer_plots SET status='archived',is_selected=FALSE,latitude=NULL,longitude=NULL,
    location_permission_at=NULL,updated_at=clock_timestamp() WHERE id=plot_id;
  IF was_selected THEN
    UPDATE public.farmer_plots SET is_selected=TRUE,updated_at=clock_timestamp()
      WHERE id=(SELECT id FROM public.farmer_plots WHERE farmer_user_id=subject AND status='active'
        ORDER BY created_at,id LIMIT 1);
  END IF;
  INSERT INTO public.audit_logs(actor_user_id,action,target_entity,target_id)
    VALUES(subject,'PLOT_ARCHIVED','farmer_plots',plot_id);
  RETURN TRUE;
END $$;

CREATE FUNCTION km_private.select_farmer_plot(subject UUID, plot_id UUID)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public,km_private SET row_security=off AS $$
BEGIN
  PERFORM 1 FROM public.users WHERE id=subject AND role='farmer' AND is_active
    AND is_verified AND account_state='active' FOR UPDATE;
  IF NOT FOUND OR NOT EXISTS(SELECT 1 FROM public.farmer_plots
      WHERE id=plot_id AND farmer_user_id=subject AND status='active') THEN RETURN FALSE; END IF;
  UPDATE public.farmer_plots SET is_selected=FALSE,updated_at=clock_timestamp()
    WHERE farmer_user_id=subject AND is_selected;
  UPDATE public.farmer_plots SET is_selected=TRUE,updated_at=clock_timestamp() WHERE id=plot_id;
  INSERT INTO public.audit_logs(actor_user_id,action,target_entity,target_id)
    VALUES(subject,'PLOT_SELECTED','farmer_plots',plot_id);
  RETURN TRUE;
END $$;

REVOKE ALL ON FUNCTION km_private.create_farmer_plot(UUID,TEXT,TEXT,TEXT,NUMERIC,TEXT,TEXT,TEXT,TEXT,TEXT,NUMERIC,NUMERIC,BOOLEAN,DATE,TEXT,TEXT),
  km_private.farmer_plots_for(UUID),km_private.farmer_plot_for(UUID,UUID),
  km_private.update_farmer_plot(UUID,UUID,TEXT,TEXT,TEXT,NUMERIC,TEXT,TEXT,TEXT,TEXT,TEXT,NUMERIC,NUMERIC,BOOLEAN,DATE,TEXT,TEXT),
  km_private.archive_farmer_plot(UUID,UUID),km_private.select_farmer_plot(UUID,UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION km_private.create_farmer_plot(UUID,TEXT,TEXT,TEXT,NUMERIC,TEXT,TEXT,TEXT,TEXT,TEXT,NUMERIC,NUMERIC,BOOLEAN,DATE,TEXT,TEXT),
  km_private.farmer_plots_for(UUID),km_private.farmer_plot_for(UUID,UUID),
  km_private.update_farmer_plot(UUID,UUID,TEXT,TEXT,TEXT,NUMERIC,TEXT,TEXT,TEXT,TEXT,TEXT,NUMERIC,NUMERIC,BOOLEAN,DATE,TEXT,TEXT),
  km_private.archive_farmer_plot(UUID,UUID),km_private.select_farmer_plot(UUID,UUID) TO km_api;
COMMIT;
