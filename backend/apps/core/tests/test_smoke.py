import pytest
from django.urls import reverse

from apps.content.models import Review
from apps.core.models import SiteSettings
from apps.inquiries.models import Inquiry
from conftest import TourDayFactory

pytestmark = pytest.mark.django_db

ADMIN_LISTS = [
    "tours_tour",
    "tours_tourday",
    "content_guide",
    "content_review",
    "content_faq",
    "content_partner",
    "content_gallerypost",
    "content_stat",
    "inquiries_inquiry",
    "auth_user",
]


def test_site_settings_is_singleton():
    SiteSettings.objects.create(brand_name="A")
    SiteSettings(brand_name="B").save()
    assert SiteSettings.objects.count() == 1
    assert SiteSettings.load().brand_name == "B"


def test_whatsapp_url_encodes_text():
    s = SiteSettings(whatsapp="996555000000")
    assert s.whatsapp_url("Hi & bye") == "https://wa.me/996555000000?text=Hi%20%26%20bye"
    assert SiteSettings().whatsapp_url() == ""


@pytest.mark.parametrize("model", ADMIN_LISTS)
def test_admin_changelists_open(admin_client, model):
    TourDayFactory()
    Review.objects.create(author_name="A", text="t")
    Inquiry.objects.create(name="A", email="a@example.com")
    assert admin_client.get(reverse(f"admin:{model}_changelist")).status_code == 200


def test_admin_change_forms_open(admin_client):
    day = TourDayFactory()
    assert (
        admin_client.get(reverse("admin:tours_tour_change", args=[day.tour.pk])).status_code == 200
    )
    assert admin_client.get(reverse("admin:tours_tourday_change", args=[day.pk])).status_code == 200
    resp = admin_client.get(reverse("admin:core_sitesettings_changelist"))
    assert resp.status_code == 302  # singleton: list redirects to the form


def test_admin_is_russian(admin_client):
    resp = admin_client.get(reverse("admin:tours_tour_changelist"))
    assert "Туры" in resp.content.decode()


@pytest.mark.parametrize("url", ["/", "/tours/", "/api/docs/", "/api/schema/", "/api/v1/settings/"])
def test_public_pages_open(client, url):
    assert client.get(url).status_code == 200


def test_tour_page_and_staff_preview(client, admin_client):
    day = TourDayFactory(tour__is_published=False)
    url = day.tour.get_absolute_url()
    assert client.get(url).status_code == 404
    assert admin_client.get(url).status_code == 200


def test_settings_api_exposes_map_config(client, settings):
    settings.MAP = {**settings.MAP, "STYLE_URL": "https://tiles.example.com/style.json"}
    s = SiteSettings.load()
    s.map_3d_mode = "desktop"
    s.save()

    data = client.get("/api/v1/settings/").json()["map"]

    assert data["style_url"] == "https://tiles.example.com/style.json"
    assert data["terrain_3d"] == "desktop"
    assert data["terrain"]["encoding"] == "terrarium"
    assert len(data["topo"]["tiles"]) == 3


def test_tour_page_embeds_route_map(client):
    day = TourDayFactory()
    html = client.get(day.tour.get_absolute_url()).content.decode()
    assert 'data-island="route-map"' in html
    assert 'id="route-props"' in html
