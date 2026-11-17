"""Live weather via Open-Meteo (free, no key) or OpenWeather (key required).

Pest-risk indicators are simple published rules of thumb (warm + humid
favours sucking pests and fungal outbreaks; heavy rain washes off sprays) and
are labelled as advisory. If the provider is unreachable, the API returns an
explicit 'unavailable' status — no invented values.
"""
import httpx

from ..config import get_settings

settings = get_settings()


class WeatherUnavailable(RuntimeError):
    pass


def fetch(lat: float, lon: float) -> dict:
    try:
        if settings.weather_provider == "openweather":
            if not settings.weather_api_key:
                raise WeatherUnavailable("WEATHER_API_KEY not configured for OpenWeather")
            r = httpx.get("https://api.openweathermap.org/data/2.5/weather", timeout=10, params={
                "lat": lat, "lon": lon, "appid": settings.weather_api_key, "units": "metric"})
            r.raise_for_status()
            j = r.json()
            current = {"temperature_c": j["main"]["temp"], "humidity_pct": j["main"]["humidity"],
                       "rainfall_mm": (j.get("rain") or {}).get("1h", 0.0), "wind_kmh": round(j["wind"]["speed"] * 3.6, 1),
                       "description": j["weather"][0]["description"]}
            return {"provider": "openweather", "current": current, "daily": [], "raw": j}
        r = httpx.get("https://api.open-meteo.com/v1/forecast", timeout=10, params={
            "latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 7,
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,relative_humidity_2m_mean"})
        r.raise_for_status()
        j = r.json()
        c, d = j["current"], j["daily"]
        current = {"temperature_c": c["temperature_2m"], "humidity_pct": c["relative_humidity_2m"],
                   "rainfall_mm": c["precipitation"], "wind_kmh": c["wind_speed_10m"],
                   "description": WMO.get(c.get("weather_code"), "—"), "time": c["time"]}
        daily = [{"date": d["time"][i], "t_max": d["temperature_2m_max"][i], "t_min": d["temperature_2m_min"][i],
                  "rain_mm": d["precipitation_sum"][i], "rh_mean": (d.get("relative_humidity_2m_mean") or [None] * 7)[i]}
                 for i in range(len(d["time"]))]
        return {"provider": "open-meteo", "current": current, "daily": daily, "raw": {"timezone": j.get("timezone")}}
    except WeatherUnavailable:
        raise
    except Exception as e:
        raise WeatherUnavailable(f"Weather service unreachable: {e.__class__.__name__}") from e


def pest_risk(current: dict, daily: list[dict]) -> list[dict]:
    t, rh, rain = current.get("temperature_c"), current.get("humidity_pct"), current.get("rainfall_mm") or 0
    week_rain = sum((x.get("rain_mm") or 0) for x in daily[:3])
    out = []
    if t is not None and rh is not None:
        if 25 <= t <= 32 and rh >= 75:
            out.append({"risk": "high", "title": "Warm and humid",
                        "detail": "Favours planthoppers, aphids, whitefly and fungal diseases. Scout more often."})
        elif t > 32 and rh < 50:
            out.append({"risk": "moderate", "title": "Hot and dry",
                        "detail": "Favours mites and thrips. Check leaf undersides; avoid water stress."})
        else:
            out.append({"risk": "low", "title": "No strong weather trigger",
                        "detail": "Conditions are not especially favourable to common pests right now."})
    if week_rain >= 20 or rain >= 5:
        out.append({"risk": "info", "title": "Rain expected",
                    "detail": "Rain can wash off sprays — delay spraying until a dry window of 6+ hours."})
    if (current.get("wind_kmh") or 0) > 15:
        out.append({"risk": "info", "title": "Windy", "detail": "Avoid spraying in wind above ~15 km/h (drift)."})
    return out


WMO = {0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Rime fog",
       51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
       71: "Light snow", 73: "Snow", 75: "Heavy snow", 80: "Rain showers", 81: "Heavy showers", 82: "Violent showers",
       95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm"}
