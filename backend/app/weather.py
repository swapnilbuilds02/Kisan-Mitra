"""Plot-scoped weather context without an enabled external provider."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class WeatherLocation:
    state: str
    district: str
    latitude: float | None = None
    longitude: float | None = None

    @property
    def precision(self) -> str:
        return 'coordinates' if self.latitude is not None else 'district'


@dataclass(frozen=True)
class WeatherObservation:
    source: str
    observed_at: datetime
    expires_at: datetime
    temperature_c: float | None
    rainfall_mm: float | None
    summary: str
    units: str = 'metric'
    confidence: str | None = None
    forecast_for: datetime | None = None


class WeatherProvider(Protocol):
    def fetch(self, location: WeatherLocation) -> WeatherObservation: ...


class WeatherContextService:
    """An injected provider only. Cache entries include farmer, plot, and location."""

    def __init__(self, provider: WeatherProvider | None = None, *, clock=None) -> None:
        self.provider = provider
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._cache: dict[tuple, WeatherObservation] = {}
        self._lock = Lock()

    def context(self, farmer_id: UUID, plot: dict) -> dict:
        location = WeatherLocation(
            state=plot['state'], district=plot['district'],
            latitude=float(plot['latitude']) if plot.get('location_permission') and plot.get('latitude') is not None else None,
            longitude=float(plot['longitude']) if plot.get('location_permission') and plot.get('longitude') is not None else None,
        )
        key = (farmer_id, plot['id'], location.state, location.district, location.latitude, location.longitude)
        now = self.clock()
        with self._lock:
            cached = self._cache.get(key)
        if cached and cached.expires_at > now:
            return self._result(plot, location, cached, 'current')
        if self.provider is not None:
            try:
                observation = self.provider.fetch(location)
                if (not observation.source or observation.units != 'metric' or observation.observed_at > now or
                    observation.expires_at <= now or observation.expires_at > now + timedelta(hours=6)):
                    raise ValueError('Invalid provider observation')
                with self._lock:
                    self._cache[key] = observation
                return self._result(plot, location, observation, 'current')
            except Exception:
                pass  # Provider failures never create invented weather values.
        if cached and now - cached.expires_at <= timedelta(hours=6):
            return self._result(plot, location, cached, 'stale')
        return {'plot_id': str(plot['id']), 'status': 'unavailable',
                'location_precision': location.precision, 'source': None,
                'observed_at': None, 'expires_at': None, 'temperature_c': None,
                'rainfall_mm': None, 'summary': None, 'units': 'metric',
                'confidence': None, 'forecast_for': None}

    @staticmethod
    def _result(plot: dict, location: WeatherLocation, observation: WeatherObservation, status: str) -> dict:
        return {'plot_id': str(plot['id']), 'status': status,
                'location_precision': location.precision, 'source': observation.source,
                'observed_at': observation.observed_at.isoformat(),
                'expires_at': observation.expires_at.isoformat(),
                'temperature_c': observation.temperature_c,
                'rainfall_mm': observation.rainfall_mm, 'summary': observation.summary,
                'units': observation.units, 'confidence': observation.confidence,
                'forecast_for': observation.forecast_for.isoformat() if observation.forecast_for else None}
