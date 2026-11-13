"""Real weather from Open-Meteo (free, no key).

Geocoding and forecast data are fetched from Open-Meteo.
Precaution rules are based on real forecast numbers.
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
GEOCODE_CACHE_SECONDS = 3600
RATE_LIMIT_COOLDOWN_SECONDS = 300

_cache = {}
_geocode_cache = {}

_lock = threading.Lock()
_forecast_locks = {}

# One shared cooldown for all Open-Meteo endpoints.
_api_rate_limited_until = 0


class WeatherError(Exception):
    pass


class WeatherRateLimitError(WeatherError):
    pass


def _check_rate_limit():
    """Prevent requests while Open-Meteo is rate-limiting us."""

    with _lock:
        remaining = _api_rate_limited_until - time.time()

    if remaining > 0:
        log.warning(
            "Open-Meteo request skipped. Cooldown remaining: %s seconds",
            int(remaining)
        )
        raise WeatherRateLimitError("rate limited")


def _get(url: str, params: dict) -> dict:
    """Make a request while respecting the shared API cooldown."""

    global _api_rate_limited_until

    _check_rate_limit()

    try:
        response = requests.get(
            url,
            params=params,
            timeout=TIMEOUT_SECONDS
        )

        log.info(
            "Open-Meteo response: status=%s host=%s",
            response.status_code,
            url.split("/")[2]
        )

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")

            try:
                cooldown = float(retry_after)
            except (TypeError, ValueError):
                cooldown = RATE_LIMIT_COOLDOWN_SECONDS

            cooldown = max(30, min(cooldown, 300))

            with _lock:
                _api_rate_limited_until = max(
                    _api_rate_limited_until,
                    time.time() + cooldown
                )

            log.warning(
                "Open-Meteo rate limit reached. Global cooldown: %s seconds",
                cooldown
            )

            raise WeatherRateLimitError("rate limited")

        response.raise_for_status()
        return response.json()

    except WeatherRateLimitError:
        raise

    except requests.RequestException as exc:
        log.exception(
            "Open-Meteo network/API failure: %s - %s",
            type(exc).__name__,
            url.split("/")[2]
        )
        raise WeatherError("unavailable") from exc

    except ValueError as exc:
        log.exception("Open-Meteo JSON parsing failure: %s", exc)
        raise WeatherError("unavailable") from exc


def geocode(name: str, state: str = "", limit: int = 5) -> list:
    """Find places in India matching a location name."""

    name = " ".join((name or "").split())[:80]
    state = " ".join((state or "").split())

    if len(name) < 2:
        return []

    key = (name.lower(), state.lower(), limit)
    now = time.time()

    with _lock:
        hit = _geocode_cache.get(key)

        if hit and now - hit[0] < GEOCODE_CACHE_SECONDS:
            return [dict(place) for place in hit[1]]

    data = _get(
        GEOCODE_URL,
        {
            "name": name,
            "count": 10,
            "language": "en",
            "format": "json"
        }
    )

    places = [
        r for r in (data.get("results") or [])
        if r.get("country_code") == "IN"
    ]

    if state:
        places.sort(
            key=lambda r: 0 if state.lower() in
            str(r.get("admin1", "")).lower() else 1
        )

    out = []

    for r in places[:limit]:
        label = ", ".join(
            x for x in (
                r.get("name"),
                r.get("admin2"),
                r.get("admin1")
            ) if x
        )

        out.append({
            "name": r.get("name"),
            "state": r.get("admin1", ""),
            "latitude": r["latitude"],
            "longitude": r["longitude"],
            "label": label
        })

    with _lock:
        _geocode_cache[key] = (time.time(), out)

    return [dict(place) for place in out]


def forecast(latitude: float, longitude: float) -> dict:
    """Get current conditions and a four-day forecast."""

    key = (round(latitude, 2), round(longitude, 2))

    with _lock:
        request_lock = _forecast_locks.setdefault(
            key,
            threading.Lock()
        )

    with request_lock:
        now = time.time()

        with _lock:
            hit = _cache.get(key)

            if hit and now - hit[0] < CACHE_SECONDS:
                return hit[1]

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": "auto",
            "forecast_days": 4,
            "current": (
                "temperature_2m,relative_humidity_2m,"
                "precipitation,wind_speed_10m"
            ),
            "daily": (
                "temperature_2m_max,temperature_2m_min,"
                "precipitation_sum,precipitation_probability_max,"
                "wind_speed_10m_max"
            )
        }

        data = _get(FORECAST_URL, params)

        if "current" not in data or "daily" not in data:
            raise WeatherError("bad reply")

        with _lock:
            _cache[key] = (time.time(), data)

        return data


def precaution_keys(data: dict) -> list:
    """Choose precaution translation keys from real forecast numbers."""

    cur = data.get("current", {})
    daily = data.get("daily", {})

    def val(series, i, default=0):
        try:
            v = (daily.get(series) or [])[i]
            return default if v is None else v
        except (IndexError, TypeError):
            return default

    keys = []

    temp_max = max(
        [val("temperature_2m_max", i, -99) for i in range(3)]
        + [cur.get("temperature_2m") or -99]
    )

    temp_min = min(
        [val("temperature_2m_min", i, 99) for i in range(3)]
    )

    rain_next = [
        val("precipitation_sum", i) for i in range(3)
    ]

    prob_next = [
        val("precipitation_probability_max", i) for i in range(3)
    ]

    wind_max = max(
        [val("wind_speed_10m_max", i) for i in range(3)]
        + [cur.get("wind_speed_10m") or 0]
    )

    if temp_max >= 38:
        keys.append("wp.heat")

    if temp_min <= 10:
        keys.append("wp.cold")

    if max(rain_next) >= 50:
        keys.append("wp.rain")
    elif prob_next[0] >= 60 or prob_next[1] >= 70:
        keys.append("wp.rain_soon")

    if wind_max >= 40:
        keys.append("wp.wind")

    if (cur.get("relative_humidity_2m") or 0) >= 85:
        keys.append("wp.humid")

    if sum(rain_next) < 2 and max(prob_next) < 20 and temp_max >= 30:
        keys.append("wp.dry")

    return keys or ["wp.ok"]