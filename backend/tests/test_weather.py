import httpx

from app.services import weather


class Resp:
    def __init__(self, status, payload=None):
        self.status_code, self._p = status, payload
        self.request = httpx.Request("GET", "https://x")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=self.request, response=httpx.Response(self.status_code, request=self.request))

    def json(self):
        return self._p


METNO = {"properties": {"timeseries": [
    {"time": "2026-11-17T15:00:00Z", "data": {"instant": {"details": {"air_temperature": 25.4, "relative_humidity": 45.7, "wind_speed": 2}},
     "next_1_hours": {"summary": {"symbol_code": "clearsky_night"}, "details": {"precipitation_amount": 0.4}},
     "next_6_hours": {"summary": {"symbol_code": "x"}, "details": {"precipitation_amount": 9}}}},
    {"time": "2026-11-17T16:00:00Z", "data": {"instant": {"details": {"air_temperature": 24.0, "relative_humidity": 50}},
     "next_1_hours": {"details": {"precipitation_amount": 0.6}}}},
    {"time": "2026-11-19T00:00:00Z", "data": {"instant": {"details": {"air_temperature": 18.0, "relative_humidity": 60}},
     "next_6_hours": {"details": {"precipitation_amount": 3.0}}}},
]}}


def test_fallback_to_metno(monkeypatch):
    weather._cache.clear()
    calls = []

    def fake_get(url, **kw):
        calls.append(url)
        return Resp(429) if "open-meteo" in url else Resp(200, METNO)

    monkeypatch.setattr(weather.httpx, "get", fake_get)
    d = weather.fetch(21.15, 79.09)
    assert d["provider"] == "met.no"
    assert d["current"]["temperature_c"] == 25.4 and d["current"]["wind_kmh"] == 7.2
    assert d["daily"][0]["rain_mm"] == 1.0 and d["daily"][0]["t_max"] == 25.4   # hourly rows only, 6h not double-counted
    assert d["daily"][1]["rain_mm"] == 3.0                                       # 6-hourly row counted
    assert weather.pest_risk(d["current"], d["daily"])
    weather.fetch(21.15, 79.09)  # cached
    assert len(calls) == 2


def test_both_providers_down(monkeypatch):
    weather._cache.clear()
    monkeypatch.setattr(weather.httpx, "get", lambda url, **kw: Resp(503))
    try:
        weather.fetch(1.0, 2.0)
        assert False
    except weather.WeatherUnavailable as e:
        assert "HTTP 503" in str(e)
