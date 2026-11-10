import io
import json
import urllib.error
from decimal import Decimal
from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.tours.forms import TourDayAdminForm
from apps.tours.geo import haversine_km, simplify, total_ascent_m
from apps.tours.models import TrackSource
from apps.tours.services.errors import RoutingError
from apps.tours.services.routing import apply_route, build_route
from conftest import TourDayFactory

KARAKOL = {"lat": 42.4907, "lng": 78.3936, "name": "Karakol"}
ARASHAN = {"lat": 42.3747, "lng": 78.6186, "name": "Altyn-Arashan"}

GPX = b"""<?xml version="1.0"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <wpt lat="42.3747" lon="78.6186"><name>Arashan</name></wpt>
  <wpt lat="42.2846" lon="78.5203"><name>Ala-Kul</name></wpt>
  <trk><trkseg>
    <trkpt lat="42.3747" lon="78.6186"><ele>3000</ele></trkpt>
    <trkpt lat="42.3300" lon="78.5800"><ele>3400</ele></trkpt>
    <trkpt lat="42.2846" lon="78.5203"><ele>3550</ele></trkpt>
  </trkseg></trk>
</gpx>"""


def ors_response(coords, distance_m=12345.0, ascent=987.4):
    body = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {"summary": {"distance": distance_m}, "ascent": ascent},
            }
        ],
    }
    response = io.BytesIO(json.dumps(body).encode())
    response.__enter__ = lambda self=response: self
    response.__exit__ = lambda *a: None
    return response


@pytest.fixture
def ors_key(settings):
    settings.ORS_API_KEY = "test-key"
    settings.ORS_BASE_URL = "https://api.heigit.org/openrouteservice"


# --- geometry -------------------------------------------------------------------


def test_haversine_known_distance():
    # Bishkek -> Karakol is ~320 km in a straight line
    assert 300 < haversine_km([74.5698, 42.8746], [78.3936, 42.4907]) < 340


def test_ascent_ignores_jitter():
    coords = [[0, 0, 100], [0, 0, 101], [0, 0, 100], [0, 0, 150], [0, 0, 140], [0, 0, 160]]
    assert total_ascent_m(coords) == 70  # +50 then +20; the 1 m wobble is ignored
    assert total_ascent_m([[0, 0], [1, 1]]) is None


def test_simplify_drops_collinear_points():
    line = [[0, 0], [0.5, 0.0000001], [1, 0]]
    assert simplify(line) == [[0, 0], [1, 0]]


# --- build_route ----------------------------------------------------------------


def test_straight_line_has_distance_and_no_ascent():
    result = build_route(TrackSource.MANUAL, [KARAKOL, ARASHAN])
    assert result.track["coordinates"] == [[78.3936, 42.4907], [78.6186, 42.3747]]
    assert Decimal("20") < result.distance_km < Decimal("25")
    assert result.ascent_m is None


def test_straight_line_needs_two_points():
    assert build_route(TrackSource.MANUAL, [KARAKOL]).track is None


def test_ors_hiking_request_and_result(ors_key):
    coords = [[78.3936, 42.4907, 1800.0], [78.5, 42.43, 2500.0], [78.6186, 42.3747, 3000.0]]
    with mock.patch("urllib.request.urlopen", return_value=ors_response(coords)) as urlopen:
        result = build_route(TrackSource.HIKING, [KARAKOL, ARASHAN])

    request = urlopen.call_args.args[0]
    assert request.full_url.endswith("/openrouteservice/v2/directions/foot-hiking/geojson")
    assert request.get_header("Authorization") == "test-key"
    body = json.loads(request.data)
    assert body["coordinates"] == [[78.3936, 42.4907], [78.6186, 42.3747]]  # lng, lat
    assert body["elevation"] is True
    assert result.track["coordinates"] == coords
    assert result.distance_km == Decimal("12.3")
    assert result.ascent_m == 987


def test_ors_without_key_explains_what_to_do(settings):
    settings.ORS_API_KEY = ""
    with pytest.raises(RoutingError, match="ORS_API_KEY"):
        build_route(TrackSource.ROAD, [KARAKOL, ARASHAN])


@pytest.mark.parametrize(
    ("code", "body", "message"),
    [
        (403, "Access denied", "лимит"),
        (404, '{"error":{"code":2010}}', "не нашёл дорогу"),
        (429, "", "Слишком много"),
    ],
)
def test_ors_http_errors_are_readable(ors_key, code, body, message):
    error = urllib.error.HTTPError("url", code, "err", {}, io.BytesIO(body.encode()))
    with (
        mock.patch("urllib.request.urlopen", side_effect=error),
        pytest.raises(RoutingError, match=message),
    ):
        build_route(TrackSource.ROAD, [KARAKOL, ARASHAN])


def test_gpx_track_distance_ascent_and_points():
    result = build_route(TrackSource.GPX, [], SimpleUploadedFile("trek.gpx", GPX))
    assert len(result.track["coordinates"]) == 3
    assert result.ascent_m == 550
    assert result.distance_km > Decimal("10")
    assert [p["name"] for p in result.waypoints] == ["Arashan", "Ala-Kul"]


def test_broken_gpx_is_rejected():
    with pytest.raises(RoutingError, match="GPX"):
        build_route(TrackSource.GPX, [], SimpleUploadedFile("x.gpx", b"<gpx><trk>"))


# --- apply_route caching --------------------------------------------------------


@pytest.mark.django_db
def test_apply_route_rebuilds_only_when_inputs_change(ors_key):
    day = TourDayFactory(waypoints=[KARAKOL, ARASHAN], track_source=TrackSource.ROAD, track=None)
    coords = [[78.3936, 42.4907], [78.6186, 42.3747]]
    with mock.patch("urllib.request.urlopen", return_value=ors_response(coords)) as urlopen:
        assert apply_route(day) is True
        assert apply_route(day) is False  # same points + mode: no second paid call
        assert urlopen.call_count == 1

    day.waypoints = [ARASHAN, KARAKOL]
    with mock.patch("urllib.request.urlopen", return_value=ors_response(coords)) as urlopen:
        assert apply_route(day) is True
        assert urlopen.call_count == 1


@pytest.mark.django_db
def test_apply_route_keeps_numbers_typed_by_client():
    day = TourDayFactory(waypoints=[KARAKOL, ARASHAN], distance_km=Decimal("15.0"))
    apply_route(day)
    assert day.distance_km == Decimal("15.0")
    assert day.track is not None


# --- admin form and staff API ---------------------------------------------------


def form_data(day, **overrides):
    data = {
        "tour": day.tour_id,
        "day_number": day.day_number,
        "title": day.title,
        "track_source": TrackSource.MANUAL,
        "waypoints": json.dumps([KARAKOL, ARASHAN]),
    }
    return {**data, **overrides}


@pytest.mark.django_db
def test_admin_form_builds_line_and_fills_distance():
    day = TourDayFactory(waypoints=[], track=None)
    form = TourDayAdminForm(data=form_data(day), instance=day)
    assert form.is_valid(), form.errors
    saved = form.save()
    assert saved.track["type"] == "LineString"
    assert saved.distance_km is not None
    assert saved.track_key


@pytest.mark.django_db
def test_admin_form_shows_routing_error(settings):
    settings.ORS_API_KEY = ""
    day = TourDayFactory()
    form = TourDayAdminForm(data=form_data(day, track_source=TrackSource.HIKING), instance=day)
    assert not form.is_valid()
    assert "ORS_API_KEY" in str(form.errors["track_source"])


@pytest.mark.django_db
def test_admin_form_gpx_upload_fills_points():
    day = TourDayFactory(waypoints=[], track=None)
    form = TourDayAdminForm(
        data=form_data(day, track_source=TrackSource.GPX, waypoints="[]"),
        files={"gpx_file": SimpleUploadedFile("trek.gpx", GPX)},
        instance=day,
    )
    assert form.is_valid(), form.errors
    saved = form.save()
    assert len(saved.waypoints) == 2
    assert saved.ascent_m == 550


@pytest.mark.django_db
def test_route_build_api_is_staff_only(api, admin_user):
    url = reverse("v1:route-build")
    payload = {"source": "manual", "waypoints": [KARAKOL, ARASHAN]}
    assert api.post(url, payload, format="json").status_code == 403

    api.force_authenticate(admin_user)
    resp = api.post(url, payload, format="json")
    assert resp.status_code == 200
    assert resp.json()["track"]["type"] == "LineString"


@pytest.mark.django_db
def test_route_build_api_returns_422_with_message(api, admin_user, settings):
    settings.ORS_API_KEY = ""
    api.force_authenticate(admin_user)
    payload = {"source": "hiking", "waypoints": [KARAKOL, ARASHAN]}
    resp = api.post(reverse("v1:route-build"), payload, format="json")
    assert resp.status_code == 422
    assert "ORS_API_KEY" in resp.json()["detail"]


@pytest.mark.django_db
def test_route_gpx_api(api, admin_user):
    api.force_authenticate(admin_user)
    resp = api.post(
        reverse("v1:route-gpx"),
        {"file": SimpleUploadedFile("trek.gpx", GPX)},
        format="multipart",
    )
    assert resp.status_code == 200
    assert resp.json()["ascent_m"] == 550


@pytest.mark.django_db
def test_admin_day_page_renders_map_editor(admin_client):
    day = TourDayFactory()
    html = admin_client.get(reverse("admin:tours_tourday_change", args=[day.pk])).content.decode()
    assert 'data-island="route-editor"' in html
    assert "route-editor" in html  # vite asset tag


def _upload(name, content):
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile(name, content)


KML_LINE = b"""<?xml version="1.0"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Placemark><name>Camp</name><Point><coordinates>78.61,42.37,2600</coordinates></Point></Placemark>
<Placemark><name>Track</name><LineString><coordinates>
78.61,42.37,2600 78.58,42.34,3300 78.545,42.326,3920</coordinates></LineString></Placemark>
</Document></kml>"""

KML_POINTS = b"""<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Placemark><name>Altyn-Arashan</name>
<Point><coordinates>78.611,42.373</coordinates></Point></Placemark>
<Placemark><name>Ala-Kul pass</name>
<Point><coordinates>78.545,42.326</coordinates></Point></Placemark>
<Placemark><name>Ala-Kul lake</name>
<Point><coordinates>78.527,42.319</coordinates></Point></Placemark>
</Document></kml>"""


def test_kml_track_from_maps_me():
    from apps.tours.services.routing import gpx_route

    result = gpx_route(_upload("route.kml", KML_LINE))
    assert result.track["type"] == "LineString" and result.distance_km > 0
    assert result.ascent_m >= 1300


def test_kml_bookmarks_become_day_points():
    from apps.tours.services.routing import gpx_route

    result = gpx_route(_upload("bookmarks.kml", KML_POINTS))
    assert [p["name"] for p in result.waypoints] == [
        "Altyn-Arashan",
        "Ala-Kul pass",
        "Ala-Kul lake",
    ]


def test_kmz_archive():
    import io
    import zipfile

    from apps.tours.services.routing import gpx_route

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("doc.kml", KML_POINTS)
    result = gpx_route(_upload("export.kmz", buffer.getvalue()))
    assert len(result.waypoints) == 3
