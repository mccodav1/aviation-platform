from datetime import datetime, timezone

import requests

from django.core.cache import cache

import logging

logger = logging.getLogger(__name__)

METAR_URL = "https://aviationweather.gov/api/data/metar"

WIND_UNAVAILABLE = "Wind data unavailable"

def format_altimeter(metar):
    # The API reports altim in hectopascals (e.g. 1017.4), but US METARs
    # are conventionally read in inches of mercury (e.g. "A3004" -> 30.04
    # in Hg) - convert rather than show the raw hPa value.
    altim_hpa = metar.get("altim")
    if altim_hpa is None:
        return None

    return f'{altim_hpa / 33.8639:.2f}"'

def format_wind(metar):
    speed = metar.get("wspd")
    direction = metar.get("wdir")
    gust = metar.get("wgst")

    if speed in (None, 0):
        return "Calm"

    # Light, shifting winds are reported as wdir "VRB" rather than a
    # number. Only that says "Variable" - a missing or unrecognized
    # direction says so, rather than guessing.
    if direction == "VRB":
        wind = f"Variable at {speed} kt"
    elif isinstance(direction, (int, float)):
        wind = f"{direction:03.0f}° at {speed} kt"
    else:
        return WIND_UNAVAILABLE

    if gust:
        wind += f" (gusts {gust} kt)"

    return wind

def format_sky(metar):
    # The API reports sky as a list of cloud layers, each with its own
    # coverage code and base height in feet AGL - surface both per layer
    # rather than collapsing to one code, since "BKN" alone doesn't say
    # whether that ceiling is at 500 ft or 15,000 ft.
    clouds = metar.get("clouds", [])
    if not clouds:
        return "Clear"

    layers = []
    for cloud in clouds:
        cover = cloud.get("cover")
        base = cloud.get("base")
        if not cover:
            continue
        layers.append(f"{cover} {base:,} ft" if base is not None else cover)

    return ", ".join(layers) if layers else "Clear"

def format_observed(metar):
    # Deliberately not baked into the cached metar dict in get_metar()
    # below - the METAR itself is cached for 5 minutes, but "how long
    # ago" needs to keep counting up on every request within that
    # window, not freeze at whatever it was when the cache was filled.
    obs_time = metar.get("obsTime")
    if obs_time is None:
        return None

    observed = datetime.fromtimestamp(obs_time, tz=timezone.utc)
    minutes = int((datetime.now(timezone.utc) - observed).total_seconds() // 60)

    if minutes < 1:
        return "Just now"
    if minutes < 60:
        return f"{minutes} min ago"

    hours = minutes // 60
    return f"{hours} hr ago" if hours == 1 else f"{hours} hrs ago"

def _formatted(formatter, metar, station, fallback=None):
    try:
        return formatter(metar)
    except (TypeError, ValueError, KeyError, AttributeError):
        logger.exception("Couldn't format %s for %s", formatter.__name__, station)
        return fallback


def get_metar(station, org_name=None):
    cache_key = f"metar:{station}"

    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Using cached METAR for {station}: {cached}")
        return cached

    try:
        response = requests.get(
            METAR_URL,
            params={
                "ids": station,
                "format": "json",
            },
            headers={
                # Identifies the calling site to aviationweather.gov, per
                # their API etiquette - not this deployment's own name, so
                # it's built from the Organization rather than hardcoded
                # for one club.
                "User-Agent": f"Aviation Website: {org_name}" if org_name else "Aviation Website",
            },
            timeout=5,
        )
        response.raise_for_status()

        data = response.json()
        logger.debug("METAR response for %s: %s", station, data)

        if not data:
            return None

        metar = data[0]

        # Each one on its own, so a value in a shape we don't expect
        # costs only that line of the panel, not the whole report.
        metar["wind_text"] = _formatted(format_wind, metar, station, fallback=WIND_UNAVAILABLE)
        metar["altim_text"] = _formatted(format_altimeter, metar, station)
        metar["sky_text"] = _formatted(format_sky, metar, station)

        cache.set(cache_key, metar, 300)

        return metar

    except (requests.RequestException, ValueError):
        logger.exception(f"Failed to retrieve METAR for {station}")
        return None