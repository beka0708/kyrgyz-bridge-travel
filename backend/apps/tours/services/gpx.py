"""Minimal GPX reader: tracks (trk/trkseg/trkpt), falling back to routes (rte/rtept)."""

import contextlib
from xml.etree import ElementTree

from .errors import RoutingError

MAX_GPX_BYTES = 10 * 1024 * 1024


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def parse_gpx(file) -> tuple[list[list[float]], list[str]]:
    """Return ([[lng, lat, ele?], ...], [waypoint names]) from an uploaded GPX file."""
    file.seek(0)
    raw = file.read(MAX_GPX_BYTES + 1)
    if len(raw) > MAX_GPX_BYTES:
        raise RoutingError("GPX-файл больше 10 МБ.")
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError as exc:
        raise RoutingError("Не удалось прочитать GPX-файл: неверный формат.") from exc

    def points(tag):
        result = []
        for el in root.iter():
            if _local(el.tag) != tag:
                continue
            try:
                point = [float(el.attrib["lon"]), float(el.attrib["lat"])]
            except (KeyError, ValueError):
                continue
            ele = next((c.text for c in el if _local(c.tag) == "ele"), None)
            if ele is not None:
                with contextlib.suppress(ValueError):
                    point.append(float(ele))
            result.append(point)
        return result

    coords = points("trkpt") or points("rtept")
    names = [
        c.text.strip()
        for wpt in root.iter()
        if _local(wpt.tag) == "wpt"
        for c in wpt
        if _local(c.tag) == "name" and c.text
    ]
    return coords, names
