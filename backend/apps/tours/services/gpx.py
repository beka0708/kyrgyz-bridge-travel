"""Route files from apps: GPX (tracks, routes, waypoints) and KML/KMZ (maps.me, Organic Maps,
Google My Maps, Wikiloc exports: LineString / gx:Track lines and Point placemarks)."""

import contextlib
import io
import zipfile
from xml.etree import ElementTree

from .errors import RoutingError

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_KML_BYTES = 20 * 1024 * 1024  # unzipped KML inside a KMZ


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _read(file) -> bytes:
    file.seek(0)
    raw = file.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise RoutingError("Файл маршрута больше 10 МБ.")
    return raw


def _xml(raw: bytes, kind: str) -> ElementTree.Element:
    try:
        return ElementTree.fromstring(raw)
    except ElementTree.ParseError as exc:
        raise RoutingError(f"Не удалось прочитать {kind}-файл: неверный формат.") from exc


def parse_track_file(file) -> tuple[list[list[float]], list[dict]]:
    """Return (line [[lng, lat, ele?], ...], named points [{"lat", "lng", "name"}, ...]).

    The line comes from a recorded track; points are waypoints / bookmarks in file order.
    """
    name = (getattr(file, "name", "") or "").lower()
    raw = _read(file)
    if name.endswith(".kmz") or raw[:2] == b"PK":
        return _parse_kml(_unzip_kml(raw))
    if name.endswith(".kml") or b"<kml" in raw[:500]:
        return _parse_kml(raw)
    return _parse_gpx(raw)


def parse_gpx(file) -> tuple[list[list[float]], list[str]]:
    """Back-compatible: ([[lng, lat, ele?], ...], [waypoint names]) from a GPX/KML/KMZ file."""
    line, points = parse_track_file(file)
    return line, [p["name"] for p in points]


def _parse_gpx(raw: bytes):
    root = _xml(raw, "GPX")

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

    line = points("trkpt") or points("rtept")
    named = []
    for wpt in root.iter():
        if _local(wpt.tag) != "wpt":
            continue
        label = next((c.text.strip() for c in wpt if _local(c.tag) == "name" and c.text), "")
        with contextlib.suppress(KeyError, ValueError):
            named.append(
                {"lat": float(wpt.attrib["lat"]), "lng": float(wpt.attrib["lon"]), "name": label}
            )
    return line, named


def _unzip_kml(raw: bytes) -> bytes:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            kml = next((n for n in archive.namelist() if n.lower().endswith(".kml")), None)
            if not kml:
                raise RoutingError("В KMZ-архиве нет KML-файла.")
            if archive.getinfo(kml).file_size > MAX_KML_BYTES:
                raise RoutingError("KML внутри KMZ слишком большой.")
            return archive.read(kml)
    except zipfile.BadZipFile as exc:
        raise RoutingError("Не удалось открыть KMZ-файл.") from exc


def _coords(text: str) -> list[list[float]]:
    """KML «lng,lat[,alt] lng,lat[,alt] …»."""
    result = []
    for chunk in (text or "").split():
        parts = chunk.split(",")
        with contextlib.suppress(ValueError):
            point = [float(parts[0]), float(parts[1])]
            if len(parts) > 2 and parts[2]:
                point.append(float(parts[2]))
            result.append(point)
    return result


def _parse_kml(raw: bytes):
    root = _xml(raw, "KML")
    line: list[list[float]] = []
    named = []
    for placemark in root.iter():
        if _local(placemark.tag) != "Placemark":
            continue
        label = next((c.text.strip() for c in placemark if _local(c.tag) == "name" and c.text), "")
        for el in placemark.iter():
            tag = _local(el.tag)
            if tag == "LineString":
                coords = next((c.text for c in el if _local(c.tag) == "coordinates"), "")
                line.extend(_coords(coords))
            elif tag == "Track":  # gx:Track: <gx:coord>lng lat alt</gx:coord>
                for c in el:
                    if _local(c.tag) == "coord" and c.text:
                        with contextlib.suppress(ValueError):
                            line.append([float(v) for v in c.text.split()[:3]])
            elif tag == "Point":
                coords = _coords(next((c.text for c in el if _local(c.tag) == "coordinates"), ""))
                if coords:
                    named.append({"lat": coords[0][1], "lng": coords[0][0], "name": label})
    return line, named
