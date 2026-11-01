"""Real weather from Open-Meteo (free, no key). Nothing here is ever generated or guessed.

  Geocoding: GET https://geocoding-api.open-meteo.com/v1/search?name=...&count=5&language=en&format=json
  Forecast : GET https://api.open-meteo.com/v1/forecast?latitude=..&longitude=..&current=..&daily=..&timezone=auto
Attribution is shown in the app ("Weather data: Open-Meteo.com").
Precaution rules below are simple thresholds applied to the REAL numbers returned.
"""

import logging
import threading
import time

import requests

log = logging.getLogger("agrivoice.weather")
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SECONDS = 15
CACHE_SECONDS = 600
_cache, _lock = {}, threading.Lock()


class WeatherError(Exception):
    pass


def _get(url: str, params: dict) -> dict:
    try:
        response = requests.get(url, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        log.warning("open-meteo request failed (%s)", url.split("/")[2])
        raise WeatherError("unavailable")


def geocode(name: str, state: str = "", limit: int = 5) -> list:
    """Places in India matching `name`, best match first. Each: {name, state, latitude, longitude, label}."""
    name = " ".join((name or "").split())[:80]
    if len(name) < 2:
        return []
    data = _get(GEOCODE_URL, {"name": name, "count": 10, "language": "en", "format": "json"})
    places = [r for r in (data.get("results") or []) if r.get("country_code") == "IN"]
    if state:
        places.sort(key=lambda r: 0 if state.lower() in str(r.get("admin1", "")).lower() else 1)
    out = []
    for r in places[:limit]:
        label = ", ".join(x for x in (r.get("name"), r.get("admin2"), r.get("admin1")) if x)
        out.append({"name": r.get("name"), "state": r.get("admin1", ""), "latitude": r["latitude"],
                    "longitude": r["longitude"], "label": label})
    return out


def forecast(latitude: float, longitude: float) -> dict:
    """Current conditions plus today and the next 3 days. Raises WeatherError if Open-Meteo cannot be reached."""
    key = (round(latitude, 2), round(longitude, 2))
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < CACHE_SECONDS:
            return hit[1]
    data = _get(FORECAST_URL, {
        "latitude": latitude, "longitude": longitude, "timezone": "auto", "forecast_days": 4,
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max",
    })
    if "current" not in data or "daily" not in data:
        raise WeatherError("bad reply")
    with _lock:
        _cache[key] = (now, data)
    return data


def precaution_keys(data: dict) -> list:
    """Translation keys (wp.*) chosen from the real forecast numbers."""
    cur, daily = data.get("current", {}), data.get("daily", {})

    def val(series, i, default=0):
        try:
            v = (daily.get(series) or [])[i]
            return default if v is None else v
        except IndexError:
            return default

    keys = []
    temp_max = max([val("temperature_2m_max", i, -99) for i in range(3)] + [cur.get("temperature_2m") or -99])
    temp_min = min([val("temperature_2m_min", i, 99) for i in range(3)])
    rain_next = [val("precipitation_sum", i) for i in range(3)]
    prob_next = [val("precipitation_probability_max", i) for i in range(3)]
    wind_max = max([val("wind_speed_10m_max", i) for i in range(3)] + [cur.get("wind_speed_10m") or 0])

    if temp_max >= 38: keys.append("wp.heat")
    if temp_min <= 10: keys.append("wp.cold")
    if max(rain_next) >= 50: keys.append("wp.rain")
    elif prob_next[0] >= 60 or prob_next[1] >= 70: keys.append("wp.rain_soon")
    if wind_max >= 40: keys.append("wp.wind")
    if (cur.get("relative_humidity_2m") or 0) >= 85: keys.append("wp.humid")
    if sum(rain_next) < 2 and max(prob_next) < 20 and temp_max >= 30: keys.append("wp.dry")
    return keys or ["wp.ok"]
