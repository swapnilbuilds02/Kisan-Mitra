"""Guarded disposable PostgreSQL plot migration, constraints and role checks.

In CI this runs after the Admin test, which leaves migrations 0001-0008 in place.
It can also run alone on a fresh, marked disposable database.
"""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

psycopg = pytest.importorskip('psycopg')
from backend.tests.postgres_test_guard import require_disposable_database
from backend.app.identity import PostgresIdentityStore
from backend.app.plots import PostgresPlotStore


def test_plot_migration_rls_constraints_and_concurrency():
    dsn = require_disposable_database(psycopg)
    migrations = Path(__file__).resolve().parents[1] / 'migrations'
    names = ('identity_foundation','auth_state','farmer_identity','password_credentials',
             'otp_recovery','farmer_onboarding','partner_applications','admin_identity')
    with psycopg.connect(dsn, autocommit=True) as connection, connection.cursor() as cursor:
        if cursor.execute("SELECT to_regclass('public.users')").fetchone() == (None,):
            for number, name in enumerate(names, 1):
                cursor.execute((migrations/f'{number:04d}_{name}.up.sql').read_text(encoding='utf-8'))
        assert cursor.execute("SELECT to_regclass('public.farmer_plots')").fetchone() == (None,)
        cursor.execute((migrations/'0009_farmer_plots.up.sql').read_text(encoding='utf-8'))
        try:
            farmer_a = cursor.execute("INSERT INTO public.users(mobile_number,role,account_state,is_verified) "
                "VALUES('9876543215','farmer','active',TRUE) RETURNING id").fetchone()[0]
            farmer_b = cursor.execute("INSERT INTO public.users(mobile_number,role,account_state,is_verified) "
                "VALUES('9876543216','farmer','active',TRUE) RETURNING id").fetchone()[0]
            partner = cursor.execute("INSERT INTO public.users(mobile_number,role,account_state,is_verified) "
                "VALUES('9876543217','shop','active',TRUE) RETURNING id").fetchone()[0]
            repository = PostgresPlotStore(PostgresIdentityStore(dsn))
            template = dict(plot_name='Upper vineyard',crop_type='grape',grape_variety='Thompson Seedless',
                area='2.5',area_unit='acre',village='Niphad',taluka='Niphad',district='Nashik',
                state='Maharashtra',latitude=None,longitude=None,location_permission=False,
                pruning_date=None,current_crop_stage='pruned',preferred_language='mr')
            with ThreadPoolExecutor(max_workers=2) as pool:
                ids = list(pool.map(lambda index: repository.create(farmer_a,
                    {**template,'plot_name':f'Vineyard {index}'}), range(2)))
            assert ids[0] and ids[1] and ids[0] != ids[1]
            assert cursor.execute('SELECT count(*) FROM public.farmer_plots WHERE farmer_user_id=%s AND is_selected',
                (farmer_a,)).fetchone() == (1,)
            assert repository.get(farmer_b, ids[0]) is None
            assert repository.get(farmer_a, ids[0])['crop_type'] == 'grape'
            assert repository.create(partner, template) is None
            assert not repository.update(farmer_b, ids[0], template)
            assert not repository.archive(farmer_b, ids[0])
            assert repository.select(farmer_a, ids[1])
            assert repository.archive(farmer_a, ids[1])
            assert cursor.execute('SELECT count(*) FROM public.farmer_plots WHERE farmer_user_id=%s AND is_selected',
                (farmer_a,)).fetchone() == (1,)
            with pytest.raises(psycopg.errors.CheckViolation):
                with connection.transaction():
                    cursor.execute("INSERT INTO public.farmer_plots(farmer_user_id,plot_name,crop_type,area,area_unit,"
                        "village,taluka,district,state,latitude,longitude) "
                        "VALUES(%s,'Invalid','grape',1,'acre','A','B','C','D',19,73)",(farmer_a,))
            cursor.execute('GRANT km_api TO CURRENT_USER')
            cursor.execute('SET ROLE km_api')
            try:
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cursor.execute('SELECT * FROM public.farmer_plots')
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cursor.execute("UPDATE public.farmer_plots SET status='archived'")
            finally:
                cursor.execute('RESET ROLE')
                cursor.execute('REVOKE km_api FROM CURRENT_USER')
        finally:
            cursor.execute('RESET ROLE')
            cursor.execute((migrations/'0009_farmer_plots.down.sql').read_text(encoding='utf-8'))
