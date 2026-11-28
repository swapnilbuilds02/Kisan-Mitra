-- Disposable database rollback only. Do not run where real Farmer plots exist.
BEGIN;
DROP FUNCTION km_private.select_farmer_plot(UUID,UUID);
DROP FUNCTION km_private.archive_farmer_plot(UUID,UUID);
DROP FUNCTION km_private.update_farmer_plot(UUID,UUID,TEXT,TEXT,TEXT,NUMERIC,TEXT,TEXT,TEXT,TEXT,TEXT,NUMERIC,NUMERIC,BOOLEAN,DATE,TEXT,TEXT);
DROP FUNCTION km_private.farmer_plot_for(UUID,UUID);
DROP FUNCTION km_private.farmer_plots_for(UUID);
DROP FUNCTION km_private.create_farmer_plot(UUID,TEXT,TEXT,TEXT,NUMERIC,TEXT,TEXT,TEXT,TEXT,TEXT,NUMERIC,NUMERIC,BOOLEAN,DATE,TEXT,TEXT);
DROP TABLE public.farmer_plots;
COMMIT;
