import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.tours.models import ListKind, TourType, validate_line_string, validate_waypoints
from conftest import TourDayFactory, TourFactory

pytestmark = pytest.mark.django_db


def test_list_shows_only_published(api):
    TourFactory(title="Visible")
    TourFactory(title="Hidden", is_published=False)

    resp = api.get(reverse("v1:tour-list"))

    assert resp.status_code == 200
    assert [t["title"] for t in resp.json()] == ["Visible"]


def test_list_filters_by_type(api):
    TourFactory(tour_type=TourType.SOLO)
    TourFactory(tour_type=TourType.GROUP)

    resp = api.get(reverse("v1:tour-list"), {"tour_type": "solo"})

    assert [t["tour_type"] for t in resp.json()] == ["solo"]


def test_detail_contains_days_lists_and_seo(api):
    tour = TourFactory(title="Ala-Kul")
    TourDayFactory(tour=tour, day_number=1)
    tour.list_items.create(kind=ListKind.INCLUDED, text="Guide")
    tour.list_items.create(kind=ListKind.GEAR, text="Boots")

    data = api.get(reverse("v1:tour-detail", args=[tour.slug])).json()

    assert [d["day_number"] for d in data["days"]] == [1]
    assert data["included"] == ["Guide"]
    assert data["gear"] == ["Boots"]
    assert data["excluded"] == []
    assert data["seo"]["title"] == "Ala-Kul"
    assert data["seo"]["image"].startswith("http")


def test_unpublished_detail_is_404(api):
    tour = TourFactory(is_published=False)
    assert api.get(reverse("v1:tour-detail", args=[tour.slug])).status_code == 404


def test_route_returns_geometry_and_bounds(api):
    day = TourDayFactory()

    data = api.get(reverse("v1:tour-route", args=[day.tour.slug])).json()

    assert data["days"][0]["waypoints"][0]["lat"] == 42.87
    assert data["bounds"] == [74.57, 42.49, 78.39, 42.87]


def test_route_without_points_has_no_bounds(api):
    day = TourDayFactory(waypoints=[])
    data = api.get(reverse("v1:tour-route", args=[day.tour.slug])).json()
    assert data["bounds"] is None


@pytest.mark.parametrize(
    "value",
    [{"lat": 1}, [{"lat": "x", "lng": 1}], [{"lat": 91, "lng": 0}], ["point"]],
)
def test_invalid_waypoints_rejected(value):
    with pytest.raises(ValidationError):
        validate_waypoints(value)


def test_line_string_validation():
    validate_line_string(None)
    validate_line_string({"type": "LineString", "coordinates": [[1, 2], [3, 4]]})
    with pytest.raises(ValidationError):
        validate_line_string({"type": "Point", "coordinates": [1, 2]})
