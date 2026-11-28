"""Farmer-owned plots. The API supplies the authenticated subject; no partner access exists."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID


class PlotStore(Protocol):
    def create(self, farmer_id: UUID, data: dict) -> UUID | None: ...
    def list(self, farmer_id: UUID) -> list[dict]: ...
    def get(self, farmer_id: UUID, plot_id: UUID) -> dict | None: ...
    def update(self, farmer_id: UUID, plot_id: UUID, data: dict) -> bool: ...
    def archive(self, farmer_id: UUID, plot_id: UUID) -> bool: ...
    def select(self, farmer_id: UUID, plot_id: UUID) -> bool: ...


class PostgresPlotStore:
    """Calls narrow migration-owned functions; km_api has no plot-table grants."""

    def __init__(self, identity_store) -> None:
        self.identity = identity_store

    @staticmethod
    def _record(cursor):
        row = cursor.fetchone()
        return dict(zip((column.name for column in cursor.description), row)) if row else None

    def create(self, farmer_id: UUID, data: dict) -> UUID | None:
        with self.identity._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT km_private.create_farmer_plot(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (farmer_id, data['plot_name'], data['crop_type'], data.get('grape_variety'),
                 data['area'], data['area_unit'], data['village'], data['taluka'], data['district'],
                 data['state'], data.get('latitude'), data.get('longitude'), data['location_permission'],
                 data.get('pruning_date'), data['current_crop_stage'], data['preferred_language']))
            return cursor.fetchone()[0]

    def list(self, farmer_id: UUID) -> list[dict]:
        with self.identity._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM km_private.farmer_plots_for(%s)", (farmer_id,))
            columns = [column.name for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get(self, farmer_id: UUID, plot_id: UUID) -> dict | None:
        with self.identity._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM km_private.farmer_plot_for(%s,%s)", (farmer_id, plot_id))
            return self._record(cursor)

    def update(self, farmer_id: UUID, plot_id: UUID, data: dict) -> bool:
        with self.identity._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT km_private.update_farmer_plot(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (farmer_id, plot_id, data['plot_name'], data['crop_type'], data.get('grape_variety'),
                 data['area'], data['area_unit'], data['village'], data['taluka'], data['district'],
                 data['state'], data.get('latitude'), data.get('longitude'), data['location_permission'],
                 data.get('pruning_date'), data['current_crop_stage'], data['preferred_language']))
            return bool(cursor.fetchone()[0])

    def archive(self, farmer_id: UUID, plot_id: UUID) -> bool:
        with self.identity._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT km_private.archive_farmer_plot(%s,%s)", (farmer_id, plot_id))
            return bool(cursor.fetchone()[0])

    def select(self, farmer_id: UUID, plot_id: UUID) -> bool:
        with self.identity._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT km_private.select_farmer_plot(%s,%s)", (farmer_id, plot_id))
            return bool(cursor.fetchone()[0])
