"""Building a day's route line once, in the admin. Visitors only read the stored result."""

import hashlib
import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings

from apps.tours.geo import line_length_km, simplify, total_ascent_m
from apps.tours.models import TrackSource

from .errors import RoutingError
from .gpx import parse_track_file

logger = logging.getLogger(__name__)

ORS_PROFILES = {
    TrackSource.ROAD: "driving-car",
    TrackSource.HIKING: "foot-hiking",
}


@dataclass
class RouteResult:
    track: dict | None
    distance_km: Decimal | None
    ascent_m: int | None
    waypoints: list[dict] | None = None  # filled from GPX when the day has no points yet


def track_key(source, waypoints, gpx_name="") -> str:
    """Fingerprint of everything a line depends on."""
    payload = json.dumps(
        {
            "source": source,
            "points": [[round(float(p["lng"]), 6), round(float(p["lat"]), 6)] for p in waypoints],
            "gpx": gpx_name or "",
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _line(coords):
    return {"type": "LineString", "coordinates": coords}


def _km(value):
    return Decimal(str(round(value, 1))) if value is not None else None


def straight_line(waypoints) -> RouteResult:
    coords = [[float(p["lng"]), float(p["lat"])] for p in waypoints]
    if len(coords) < 2:
        return RouteResult(track=None, distance_km=None, ascent_m=None)
    return RouteResult(track=_line(coords), distance_km=_km(line_length_km(coords)), ascent_m=None)


def ors_route(source, waypoints) -> RouteResult:
    if len(waypoints) < 2:
        raise RoutingError("Для построения линии нужно минимум две точки.")
    if not settings.ORS_API_KEY:
        raise RoutingError(
            "Не задан ключ OpenRouteService (ORS_API_KEY). "
            "Выберите «Прямые линии между точками» или добавьте ключ."
        )
    url = f"{settings.ORS_BASE_URL}/v2/directions/{ORS_PROFILES[source]}/geojson"
    body = {
        # ORS expects [lng, lat]; we store points as {"lat", "lng"}.
        "coordinates": [[float(p["lng"]), float(p["lat"])] for p in waypoints],
        "elevation": True,
        "instructions": False,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        method="POST",
        headers={
            "Authorization": settings.ORS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/geo+json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.ORS_TIMEOUT) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        logger.warning("ORS %s for %s: %s", exc.code, url, detail)
        raise RoutingError(_ors_error_message(exc.code, detail)) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        logger.warning("ORS unreachable: %s", exc)
        raise RoutingError("Сервис маршрутов недоступен, попробуйте позже.") from exc

    feature = data["features"][0]
    coords = [[round(c, 6) for c in point] for point in feature["geometry"]["coordinates"]]
    props = feature.get("properties", {})
    distance_m = props.get("summary", {}).get("distance")
    ascent = props.get("ascent")
    return RouteResult(
        track=_line(coords),
        distance_km=_km(distance_m / 1000) if distance_m is not None else None,
        ascent_m=round(ascent) if ascent is not None else None,
    )


def _ors_error_message(code, detail):
    if code in (401, 403):
        return "Ключ OpenRouteService неверный или дневной лимит исчерпан."
    if code == 429:
        return "Слишком много запросов к сервису маршрутов, подождите минуту."
    if code == 404 or "2010" in detail or "2009" in detail:
        return (
            "Сервис не нашёл дорогу или тропу рядом с точками. Сдвиньте точки ближе к "
            "дороге/тропе или выберите «Прямые линии между точками»."
        )
    return f"Сервис маршрутов вернул ошибку {code}."


def gpx_route(gpx_file) -> RouteResult:
    """A day from a route file (GPX, or KML/KMZ from maps.me and similar apps).

    A recorded line is used as is. A file with only bookmarks becomes the day's points in order,
    joined by straight lines: switch the day to «по пешим тропам» to route them along real trails.
    """
    line, points = parse_track_file(gpx_file)
    if len(line) < 2 and len(points) >= 2:
        line = [[p["lng"], p["lat"]] for p in points]
        waypoints = [
            {
                "lat": round(p["lat"], 6),
                "lng": round(p["lng"], 6),
                "name": p["name"] or f"Point {i}",
            }
            for i, p in enumerate(points, 1)
        ][:25]
    elif len(line) >= 2:
        start, end = line[0], line[-1]
        names = [p["name"] for p in points if p["name"]]
        waypoints = [
            {"lat": start[1], "lng": start[0], "name": names[0] if names else "Start"},
            {"lat": end[1], "lng": end[0], "name": names[-1] if len(names) > 1 else "Finish"},
        ]
    else:
        raise RoutingError("В файле нет маршрута: нужна линия трека или хотя бы две метки.")
    distance = line_length_km(line)
    ascent = total_ascent_m(line)
    track = _line([[round(c, 6) for c in point] for point in simplify(line)])
    return RouteResult(track=track, distance_km=_km(distance), ascent_m=ascent, waypoints=waypoints)


def build_route(source, waypoints, gpx_file=None) -> RouteResult:
    if source == TrackSource.GPX:
        if not gpx_file:
            raise RoutingError("Загрузите GPX-файл или выберите другой способ построения линии.")
        return gpx_route(gpx_file)
    if source in ORS_PROFILES:
        return ors_route(source, waypoints)
    return straight_line(waypoints)


def apply_route(day, *, gpx_file=None, force=False) -> bool:
    """Rebuild day.track if its inputs changed. Returns True when the line was rebuilt.

    Distance and ascent are filled only when empty, so numbers typed by the client win.
    Raises RoutingError; nothing on the day is changed in that case.
    """
    gpx = gpx_file if gpx_file is not None else day.gpx_file
    gpx_name = getattr(gpx, "name", "") if gpx else ""
    use_gpx = day.track_source == TrackSource.GPX
    key = track_key(day.track_source, day.waypoints or [], gpx_name if use_gpx else "")
    if key == day.track_key and not force:
        return False

    result = build_route(day.track_source, day.waypoints or [], gpx if use_gpx else None)
    day.track = result.track
    day.track_key = key
    if result.waypoints and not day.waypoints:
        day.waypoints = result.waypoints
        # the key must describe the points the day is saved with
        day.track_key = track_key(day.track_source, day.waypoints, gpx_name)
    if day.distance_km is None and result.distance_km is not None:
        day.distance_km = result.distance_km
    if day.ascent_m is None and result.ascent_m is not None:
        day.ascent_m = result.ascent_m
    return True
