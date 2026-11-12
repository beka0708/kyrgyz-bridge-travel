from datetime import date, timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.inquiries.models import Inquiry
from apps.tours.models import Departure, DepartureStatus
from apps.tours.services.departures import (
    by_month,
    create_departures,
    in_season,
    parse_dates,
    repeat_dates,
)
from conftest import TourFactory

pytestmark = pytest.mark.django_db


def soon(days=30):
    return timezone.localdate() + timedelta(days=days)


def test_end_date_from_duration_and_labels():
    tour = TourFactory(duration_days=6, price_from=890)
    d = Departure.objects.create(tour=tour, start_date=date(2027, 6, 28), seats_left=3)
    assert d.end_date == date(2027, 7, 3)
    assert d.dates_label == "28 Jun – 3 Jul 2027"
    assert d.weekdays_label == "Mon → Sat"
    assert d.seats_label == "3 seats left"
    assert d.price_label == "$890"
    d.price = 950
    assert d.price_label == "$950"
    d.status = DepartureStatus.FULL
    assert d.seats_label == "Sold out"


def test_upcoming_skips_past_and_hidden_tours():
    tour = TourFactory()
    hidden = TourFactory(is_published=False)
    Departure.objects.create(tour=tour, start_date=soon(-5))
    future = Departure.objects.create(tour=tour, start_date=soon())
    Departure.objects.create(tour=hidden, start_date=soon())
    assert list(Departure.objects.upcoming()) == [future]


def test_repeat_dates_within_season_and_wrapping_winter():
    days = repeat_dates(date(2027, 5, 1), 7, date(2027, 10, 31), (6, 9))
    assert days[0] == date(2027, 6, 5) and days[-1] == date(2027, 9, 25)
    assert all(6 <= d.month <= 9 for d in days)
    assert in_season(date(2027, 1, 10), 12, 3) and not in_season(date(2027, 6, 1), 12, 3)


def test_parse_dates_with_and_without_year():
    today = date(2026, 11, 11)
    assert parse_dates("14.06, 21.06.2027; 5/1", today) == [
        date(2027, 1, 5),
        date(2027, 6, 14),
        date(2027, 6, 21),
    ]
    with pytest.raises(ValidationError):
        parse_dates("31.02.2027", today)


def test_create_departures_skips_existing():
    tour = TourFactory()
    first = create_departures(tour, [soon(10), soon(20)], seats_left=8)
    again = create_departures(tour, [soon(10), soon(30)])
    assert first == (2, 0) and again == (1, 1)
    assert tour.departures.count() == 3


def test_tour_page_lists_dates_by_month_and_next_departure(client):
    tour = TourFactory()
    Departure.objects.create(tour=tour, start_date=soon(10), status=DepartureStatus.FULL)
    open_one = Departure.objects.create(tour=tour, start_date=soon(40))
    html = client.get(tour.get_absolute_url()).content.decode()
    assert 'id="dates"' in html and "Dates &amp; availability" in html
    assert f'data-departure="{open_one.pk}"' in html
    assert "Sold out" in html
    assert f"Next departure: <b>{open_one.short_label}</b>" in html  # the full one is skipped


def test_private_tour_without_dates_invites_any_day(client):
    tour = TourFactory(tour_type="solo")
    html = client.get(tour.get_absolute_url()).content.decode()
    assert "Private tour: you choose the dates" in html


def test_calendar_page_and_sitemap(client):
    tour = TourFactory(title="Song-Kul")
    d = Departure.objects.create(tour=tour, start_date=soon(15))
    html = client.get("/tours/dates/").content.decode()
    assert "Song-Kul" in html and f"?departure={d.pk}#contact" in html
    assert "/tours/dates/" in client.get("/sitemap.xml").content.decode()


def test_by_month_groups():
    tour = TourFactory()
    a = Departure.objects.create(tour=tour, start_date=date(2027, 6, 5))
    b = Departure.objects.create(tour=tour, start_date=date(2027, 7, 3))
    months = by_month([a, b])
    assert [m["label"] for m in months] == ["Jun 2027", "Jul 2027"]


def test_inquiry_with_departure_gets_dates_and_tour(api):
    tour = TourFactory()
    d = Departure.objects.create(tour=tour, start_date=soon(20))
    response = api.post(
        "/api/v1/inquiries/",
        {"name": "Anna", "email": "anna@example.com", "departure": d.pk, "tour": tour.slug},
        format="json",
    )
    assert response.status_code == 201, response.content
    inquiry = Inquiry.objects.get()
    assert inquiry.departure == d and inquiry.tour == tour
    assert (inquiry.date_from, inquiry.date_to) == (d.start_date, d.end_date)


def test_inquiry_departure_of_another_tour_is_rejected(api):
    d = Departure.objects.create(tour=TourFactory(), start_date=soon(20))
    response = api.post(
        "/api/v1/inquiries/",
        {"name": "Anna", "email": "a@example.com", "departure": d.pk, "tour": TourFactory().slug},
        format="json",
    )
    assert response.status_code == 400 and "departure" in response.json()


def test_admin_plans_a_season_with_a_preview(client):
    admin = get_user_model().objects.create_superuser("boss", "b@example.com", "pw-123456789")
    client.force_login(admin)
    tour = TourFactory(season_start=6, season_end=9, group_size_max=8)
    first = date(timezone.localdate().year + 1, 5, 1)
    url = f"/{settings.ADMIN_URL}tours/departure/plan/"
    assert client.get(url).status_code == 200
    data = {"tour": tour.pk, "first_date": first.isoformat(), "every_days": 14, "seats_left": ""}

    preview = client.post(url, data)  # step 1: only shows the dates
    assert preview.status_code == 200 and "Получится" in preview.content.decode()
    assert not tour.departures.exists()

    response = client.post(url, {**data, "confirm": "1"})  # step 2: creates them
    assert response.status_code == 302
    months = {d.start_date.month for d in tour.departures.all()}
    assert months <= {6, 7, 8, 9} and tour.departures.count() >= 8
    assert set(tour.departures.values_list("seats_left", flat=True)) == {8}  # from the tour


def test_zero_seats_closes_a_date_and_end_follows_the_tour():
    tour = TourFactory(duration_days=5)
    d = Departure.objects.create(tour=tour, start_date=soon(20), seats_left=3)
    d.seats_left = 0
    d.save()
    assert d.status == DepartureStatus.FULL
    d.seats_left, d.start_date = 2, soon(30)
    d.save()
    assert d.status == DepartureStatus.OPEN
    assert (d.end_date - d.start_date).days == 4


def test_copy_to_next_year_keeps_the_weekday(client):
    admin = get_user_model().objects.create_superuser("boss", "b@example.com", "pw-123456789")
    client.force_login(admin)
    d = Departure.objects.create(tour=TourFactory(), start_date=soon(20))
    client.post(
        f"/{settings.ADMIN_URL}tours/departure/",
        {"action": "copy_next_year", "_selected_action": [d.pk]},
    )
    copy = Departure.objects.exclude(pk=d.pk).get()
    assert copy.start_date.weekday() == d.start_date.weekday()
    assert (copy.start_date - d.start_date).days == 364
