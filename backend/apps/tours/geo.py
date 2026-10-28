"""Small geometry helpers for route data stored as JSON (no PostGIS needed)."""


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
