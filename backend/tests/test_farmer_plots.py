"""Plot API ownership, lifecycle, location permission, and weather boundaries."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Lock
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.identity import AccountState, Actor, Role
from backend.app.main import create_app
from backend.app.weather import WeatherContextService, WeatherObservation
from backend.tests.key_material import token_service
from backend.tests.test_api_foundation import FakeSessions, FakeStore, token


PLOT = dict(plot_name='Upper vineyard', crop_type='grape', grape_variety='Thompson Seedless',
    area='2.500', area_unit='acre', village='Niphad', taluka='Niphad', district='Nashik',
    state='Maharashtra', current_crop_stage='pruned', preferred_language='mr')


class IsolatedPlots:
    def __init__(self):
        self.rows = {}
        self.lock = Lock()

    def create(self, owner, data):
        with self.lock:
            plot_id = uuid4()
            self.rows[plot_id] = {**data, 'id': plot_id, 'farmer_user_id': owner,
                'status': 'active', 'is_selected': not any(x['is_selected'] and x['farmer_user_id'] == owner
                    for x in self.rows.values()),
                'location_permission_at': datetime.now(timezone.utc) if data.get('latitude') is not None else None}
            return plot_id

    def list(self, owner):
        return [row.copy() for row in self.rows.values() if row['farmer_user_id'] == owner]

    def get(self, owner, plot_id):
        row = self.rows.get(plot_id)
        return row.copy() if row and row['farmer_user_id'] == owner else None

    def update(self, owner, plot_id, data):
        with self.lock:
            row = self.rows.get(plot_id)
            if not row or row['farmer_user_id'] != owner or row['status'] != 'active': return False
            row.update(data)
            row['location_permission_at'] = datetime.now(timezone.utc) if data.get('latitude') is not None else None
            return True

    def archive(self, owner, plot_id):
        with self.lock:
            row = self.rows.get(plot_id)
            if not row or row['farmer_user_id'] != owner or row['status'] != 'active': return False
            selected = row['is_selected']
            row.update(status='archived', is_selected=False, latitude=None, longitude=None, location_permission_at=None)
            if selected:
                for candidate in self.rows.values():
                    if candidate['farmer_user_id'] == owner and candidate['status'] == 'active':
                        candidate['is_selected'] = True
                        break
            return True

    def select(self, owner, plot_id):
        with self.lock:
            row = self.rows.get(plot_id)
            if not row or row['farmer_user_id'] != owner or row['status'] != 'active': return False
            for candidate in self.rows.values():
                if candidate['farmer_user_id'] == owner: candidate['is_selected'] = False
            row['is_selected'] = True
            return True


def setup(role=Role.FARMER, state=AccountState.ACTIVE, plots=None, weather=None):
    actor = Actor(uuid4(), role, state)
    repository = plots or IsolatedPlots()
    client = TestClient(create_app(identity_store=FakeStore(actor), session_store=FakeSessions(),
        token_service=token_service(), plot_store=repository, weather_service=weather))
    headers = {'Authorization': 'Bearer ' + token(actor.id)}
    return client, actor, repository, headers


def test_farmer_multiple_plots_selection_and_archive():
    client, actor, _, headers = setup()
    one = client.post('/api/v1/farmer/plots', json=PLOT, headers=headers)
    two = client.post('/api/v1/farmer/plots', json={**PLOT, 'plot_name':'Lower vineyard'}, headers=headers)
    assert (one.status_code, two.status_code) == (201, 201)
    assert one.json()['is_selected'] and not two.json()['is_selected']
    first_id, second_id = one.json()['id'], two.json()['id']
    assert client.patch(f'/api/v1/farmer/plots/{first_id}', json={'current_crop_stage':'flowering'},
        headers=headers).status_code == 200
    assert client.get(f'/api/v1/farmer/plots/{second_id}', headers=headers).json()['current_crop_stage'] == 'pruned'
    assert client.post(f'/api/v1/farmer/plots/{second_id}/select', headers=headers).status_code == 200
    assert client.get(f'/api/v1/farmer/plots/{second_id}', headers=headers).json()['is_selected']
    assert client.post(f'/api/v1/farmer/plots/{second_id}/archive', headers=headers).status_code == 200
    assert client.get(f'/api/v1/farmer/plots/{first_id}', headers=headers).json()['is_selected']
    assert len(client.get('/api/v1/farmer/plots', headers=headers).json()) == 2
    assert client.get(f'/api/v1/farmer/plots/{first_id}/weather/context', headers=headers).json()['status'] == 'unavailable'
    assert client.post(f'/api/v1/farmer/plots/{second_id}/select', headers=headers).status_code == 404


def test_plot_update_and_forbidden_fields():
    client, _, _, headers = setup()
    plot_id = client.post('/api/v1/farmer/plots', json=PLOT, headers=headers).json()['id']
    changed = client.patch(f'/api/v1/farmer/plots/{plot_id}', json={'current_crop_stage':'flowering',
        'plot_name':'वरचा द्राक्षबाग'}, headers=headers)
    assert changed.status_code == 200 and changed.json()['current_crop_stage'] == 'flowering'
    for body in ({'farmer_user_id':str(uuid4())}, {'status':'active'}, {'is_selected':True}):
        assert client.patch(f'/api/v1/farmer/plots/{plot_id}', json=body, headers=headers).status_code == 422
    assert client.patch(f'/api/v1/farmer/plots/{plot_id}', json={'latitude':19.5}, headers=headers).status_code == 422
    assert client.patch(f'/api/v1/farmer/plots/{plot_id}', json={'latitude':19.5,'longitude':73.8}, headers=headers).status_code == 422
    assert client.patch(f'/api/v1/farmer/plots/{plot_id}', json={'latitude':19.5,'longitude':73.8,
        'location_permission':True}, headers=headers).status_code == 200
    assert client.patch(f'/api/v1/farmer/plots/{plot_id}', json={'latitude':None,'longitude':None,
        'location_permission':False}, headers=headers).json()['location_permission_at'] is None


def test_plot_access_is_bound_to_authenticated_farmer():
    repository = IsolatedPlots()
    owner, _, _, owner_headers = setup(plots=repository)
    other, _, _, other_headers = setup(plots=repository)
    created = owner.post('/api/v1/farmer/plots', json=PLOT, headers=owner_headers)
    plot_id = created.json()['id']
    assert other.get(f'/api/v1/farmer/plots/{plot_id}', headers=other_headers).status_code == 404
    assert other.get(f'/api/v1/farmer/plots/{plot_id}/weather/context', headers=other_headers).status_code == 404
    assert other.patch(f'/api/v1/farmer/plots/{plot_id}', json={'plot_name':'stolen'}, headers=other_headers).status_code == 404
    assert other.post(f'/api/v1/farmer/plots/{plot_id}/archive', headers=other_headers).status_code == 404
    assert other.get('/api/v1/farmer/plots', headers=other_headers).json() == []
    for role, state in ((Role.SHOP, AccountState.ACTIVE), (Role.CONSULTANT, AccountState.ACTIVE),
                        (Role.SHOP, AccountState.PENDING_APPROVAL), (Role.FARMER, AccountState.SUSPENDED)):
        client, _, _, headers = setup(role, state, repository)
        assert client.get('/api/v1/farmer/plots', headers=headers).status_code == 403
        assert client.get(f'/api/v1/farmer/plots/{plot_id}/weather/context', headers=headers).status_code == 403
    assert owner.get('/api/v1/farmer/plots').status_code == 401


def test_plot_validation_and_no_unconsented_coordinates():
    client, _, _, headers = setup()
    cases = ({**PLOT,'area':'0'}, {**PLOT,'area':'-1'}, {**PLOT,'crop_type':'Grape!'},
             {**PLOT,'latitude':19.5}, {**PLOT,'latitude':19.5,'longitude':73.8},
             {**PLOT,'pruning_date':'2099-01-01'})
    for body in cases:
        assert client.post('/api/v1/farmer/plots', json=body, headers=headers).status_code == 422
    assert client.get('/api/v1/farmer/plots', headers=headers).json() == []


def test_weather_is_plot_scoped_and_never_fabricated():
    now = datetime(2026, 11, 27, tzinfo=timezone.utc)
    class Provider:
        def __init__(self): self.calls = []; self.fail = False
        def fetch(self, location):
            self.calls.append(location)
            if self.fail: raise TimeoutError('provider unavailable')
            return WeatherObservation('isolated-test', now, now + timedelta(minutes=30), 24.0, 0.0, 'Clear')
    current = [now]
    provider = Provider()
    service = WeatherContextService(provider, clock=lambda: current[0])
    client, _, _, headers = setup(weather=service)
    one = client.post('/api/v1/farmer/plots', json=PLOT, headers=headers).json()['id']
    two = client.post('/api/v1/farmer/plots', json={**PLOT,'plot_name':'Second', 'district':'Pune',
        'latitude':18.5,'longitude':73.8,'location_permission':True}, headers=headers).json()['id']
    assert client.get(f'/api/v1/farmer/plots/{one}/weather/context', headers=headers).json()['location_precision'] == 'district'
    assert client.get(f'/api/v1/farmer/plots/{two}/weather/context', headers=headers).json()['location_precision'] == 'coordinates'
    assert provider.calls[0].latitude is None and provider.calls[1].latitude == 18.5
    assert len(provider.calls) == 2  # Separate plot cache entries.
    provider.fail = True
    current[0] = now + timedelta(minutes=31)
    assert client.get(f'/api/v1/farmer/plots/{one}/weather/context', headers=headers).json()['status'] == 'stale'
    current[0] = now + timedelta(hours=7)
    unavailable = client.get(f'/api/v1/farmer/plots/{one}/weather/context', headers=headers).json()
    assert unavailable['status'] == 'unavailable' and unavailable['temperature_c'] is None
    assert client.get(f'/api/v1/farmer/plots/{uuid4()}/weather/context', headers=headers).status_code == 404
