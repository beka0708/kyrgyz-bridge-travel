"""Small geometry helpers for route data stored as JSON (no PostGIS needed)."""

import math

EARTH_RADIUS_KM = 6371.0088


def iter_coordinates(day):
    """Yield (lng, lat) for all waypoints and track points of a TourDay."""
    for point in day.waypoints or []:
        yield float(point["lng"]), float(point["lat"])
    if day.track:
        for lng, lat, *_ in day.track.get("coordinates", []):
            yield float(lng), float(lat)


def bounds(days):
    """[west, south, east, north] or None when the route has no geometry yet."""
    coords = [c for day in days for c in iter_coordinates(day)]
    if not coords:
        return None
    lngs, lats = zip(*coords, strict=True)
    return [min(lngs), min(lats), max(lngs), max(lats)]


def haversine_km(a, b):
    """Distance between two [lng, lat, ...] points in kilometres."""
    lng1, lat1, lng2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def line_length_km(coords):
    return sum(haversine_km(a, b) for a, b in zip(coords, coords[1:], strict=False))


def total_ascent_m(coords, threshold=3.0):
    """Sum of climbs from [lng, lat, ele] points; small GPS jitter below threshold is ignored."""
    elevations = [c[2] for c in coords if len(c) > 2 and c[2] is not None]
    if len(elevations) < 2:
        return None
    ascent, base = 0.0, elevations[0]
    for ele in elevations[1:]:
        if ele - base >= threshold:
            ascent += ele - base
            base = ele
        elif ele < base:
            base = ele
    return round(ascent)


def simplify(coords, tolerance=0.00005):
    """Ramer–Douglas–Peucker in degrees (~5 m). Keeps GPX tracks small enough for the page."""
    if len(coords) < 3:
        return coords

    def perpendicular(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        if dx == dy == 0:
            return math.hypot(p[0] - a[0], p[1] - a[1])
        t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
        return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))

    keep = [False] * len(coords)
    keep[0] = keep[-1] = True
    stack = [(0, len(coords) - 1)]
    while stack:
        start, end = stack.pop()
        index, dist = None, tolerance
        for i in range(start + 1, end):
            d = perpendicular(coords[i], coords[start], coords[end])
            if d > dist:
                index, dist = i, d
        if index is not None:
            keep[index] = True
            stack += [(start, index), (index, end)]
    return [c for c, k in zip(coords, keep, strict=True) if k]
