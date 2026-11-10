import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.content.models import Review
from apps.inquiries.models import Inquiry
from apps.stats.models import ContactClick, TourView
from conftest import TourFactory

pytestmark = pytest.mark.django_db
BROWSER = "Mozilla/5.0 (Macintosh) Safari/605"


def test_tour_view_counted_once_per_visitor_per_day(client):
    tour = TourFactory()
    for _ in range(3):
        client.get(tour.get_absolute_url(), HTTP_USER_AGENT=BROWSER)
    client.get(tour.get_absolute_url(), HTTP_USER_AGENT=BROWSER, REMOTE_ADDR="10.0.0.2")
    assert TourView.objects.get(tour=tour).views == 2


def test_bots_and_staff_are_not_counted(client):
    tour = TourFactory()
    client.get(tour.get_absolute_url(), HTTP_USER_AGENT="Googlebot/2.1")
    staff = get_user_model().objects.create_user("boss", password="x", is_staff=True)
    client.force_login(staff)
    client.get(tour.get_absolute_url(), HTTP_USER_AGENT=BROWSER)
    assert not TourView.objects.exists()


def test_contact_click_beacon(api):
    url = "/api/v1/stats/click/"
    assert (
        api.post(url, {"channel": "whatsapp"}, format="json", HTTP_USER_AGENT=BROWSER).status_code
        == 204
    )
    assert (
        api.post(url, {"channel": "pigeon"}, format="json", HTTP_USER_AGENT=BROWSER).status_code
        == 204
    )
    assert list(ContactClick.objects.values_list("channel", "clicks")) == [("whatsapp", 1)]


def test_admin_dashboard(client):
    tour = TourFactory(title="Lake trek")
    Inquiry.objects.create(name="Anna", email="a@example.com", tour=tour, tour_title=tour.title)
    Review.objects.create(
        author_name="Tom", text="Nice", rating=3, source="site", is_published=False
    )
    admin = get_user_model().objects.create_superuser("admin", "a@example.com", "x")
    client.force_login(admin)

    html = client.get(f"/{settings.ADMIN_URL}").content.decode()

    assert "Обзор сайта" in html and "Lake trek" in html
    assert "Новые заявки без ответа" in html and "Отзывы ждут проверки" in html
    assert 'class="chart"' in html


def test_demo_stats_command():
    from django.core.management import call_command

    TourFactory()
    call_command("demo_stats")
    assert Inquiry.objects.filter(utm_campaign="demo-stats").exists()
    assert TourView.objects.exists()
    call_command("demo_stats")  # re-run replaces, does not pile up
    assert Inquiry.objects.filter(utm_campaign="demo-stats").count() < 300
