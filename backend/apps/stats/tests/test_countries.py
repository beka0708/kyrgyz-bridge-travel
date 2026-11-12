from unittest import mock

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.inquiries.services import inquiry_country
from apps.stats.geo import country_for_ip, country_name, flag
from apps.stats.models import CountryVisit
from conftest import TourFactory

pytestmark = pytest.mark.django_db

BROWSER = "Mozilla/5.0 (Macintosh) Safari/605"


def test_flag_and_names():
    assert flag("KG") == "🇰🇬"
    assert country_name("KG") == "Кыргызстан" and country_name("") == "Не определена"


def test_private_ips_have_no_country():
    assert country_for_ip("127.0.0.1") == "" and country_for_ip("nonsense") == ""


@mock.patch("apps.stats.services.country_for_ip", return_value="DE")
def test_one_visit_per_visitor_per_day_on_public_pages(_geo, client):
    tour = TourFactory()
    client.get("/", HTTP_USER_AGENT=BROWSER)
    client.get(tour.get_absolute_url(), HTTP_USER_AGENT=BROWSER)  # same visitor, same day
    client.get("/robots.txt", HTTP_USER_AGENT=BROWSER)  # not an HTML page
    assert list(CountryVisit.objects.values_list("country", "visits")) == [("DE", 1)]


@mock.patch("apps.stats.services.country_for_ip", return_value="DE")
def test_bots_are_not_counted(_geo, client):
    client.get("/", HTTP_USER_AGENT="Googlebot/2.1")
    assert not CountryVisit.objects.exists()


def test_inquiry_country_falls_back_to_the_phone_code():
    with mock.patch("apps.stats.geo.country_for_ip", return_value=""):
        assert inquiry_country("10.0.0.1", "+44 7700 900123") == "GB"
        assert inquiry_country("10.0.0.1", "anna@example.com") == ""


def test_dashboard_shows_countries(client):
    from django.utils import timezone

    CountryVisit.objects.create(date=timezone.localdate(), country="GB", visits=7)
    admin = get_user_model().objects.create_superuser("boss", "b@example.com", "pw-123456789")
    client.force_login(admin)
    html = client.get(f"/{settings.ADMIN_URL}").content.decode()
    assert "Откуда заходят" in html and "Великобритания" in html and "🇬🇧" in html


def test_purge_demo_data_keeps_real_inquiries():
    from datetime import date

    from django.core.management import call_command

    from apps.inquiries.models import Inquiry
    from apps.stats.models import TourView

    tour = TourFactory()
    Inquiry.objects.create(name="Demo", email="d@example.com", utm_campaign="demo-stats")
    Inquiry.objects.create(name="Old demo", email="o@example.com", user_agent="demo-stats")
    Inquiry.objects.create(name="Real", email="r@example.com")
    TourView.objects.create(tour=tour, date=date(2026, 11, 10), views=5)
    TourView.objects.create(tour=tour, date=date(2026, 11, 11), views=2)

    call_command("purge_demo_data", stats_until="2026-11-10")  # dry run
    assert Inquiry.objects.count() == 3

    call_command("purge_demo_data", stats_until="2026-11-10", yes=True)
    assert list(Inquiry.objects.values_list("name", flat=True)) == ["Real"]
    assert list(TourView.objects.values_list("views", flat=True)) == [2]
