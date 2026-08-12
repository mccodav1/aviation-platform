import requests

from django.core.cache import cache


METAR_URL = "https://aviationweather.gov/api/data/metar"

def get_ceiling(clouds):
    ceilings = [
        cloud["base"]
        for cloud in clouds
        if cloud.get("cover") in {"BKN", "OVC", "VV"}
        and cloud.get("base") is not None
    ]

    return min(ceilings) if ceilings else None

def format_wind(metar):
    speed = metar.get("wspd")
    direction = metar.get("wdir")
    gust = metar.get("wgst")

    if speed in (None, 0):
        return "Calm"

    if direction is None:
        wind = f"Variable at {speed} kt"
    else:
        wind = f"{direction:03.0f}° at {speed} kt"

    if gust:
        wind += f", gusting {gust} kt"

    return wind

def get_metar(station="KSNS"):
    cache_key = f"metar:{station}"

    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        response = requests.get(
            METAR_URL,
            params={
                "ids": station,
                "format": "json",
            },
            headers={
                "User-Agent": "Salinas Pilots Association Website",
            },
            timeout=5,
        )
        response.raise_for_status()

        data = response.json()

        if not data:
            return None

        metar = data[0]

        metar["ceiling"] = get_ceiling(
            metar.get("clouds", [])
        )

        metar["wind_text"] = format_wind(metar)

        cache.set(cache_key, metar, 300)

        return metar

    except (requests.RequestException, ValueError):
        return None