import pytest
from django.core import mail

from apps.content.models import Review
from apps.core.models import SiteSettings
from conftest import TourFactory

pytestmark = pytest.mark.django_db
URL = "/reviews/new/"


@pytest.fixture(autouse=True)
def agency_email():
    s = SiteSettings.load()
    s.inquiry_email = "agency@example.com"
    s.save()


def data(**extra):
    return {
        "author_name": "Laura",
        "country": "Netherlands",
        "rating": "4",
        "text": "Great guides and food, the last transfer was long though.",
        "email": "laura@example.com",
        **extra,
    }


def test_review_is_saved_hidden_and_agency_notified(client, django_capture_on_commit_callbacks):
    tour = TourFactory(title="Song-Kul")
    with django_capture_on_commit_callbacks(execute=True):
        resp = client.post(URL, data(tour=tour.slug, travel_month="2026-08"))
    assert resp.status_code == 302 and resp["Location"].endswith("?sent=1&r=4")
    review = Review.objects.get()
    assert (review.is_published, review.source, review.rating, review.tour) == (
        False,
        "site",
        4,
        tour,
    )
    assert review.travel_date.isoformat() == "2026-08-01"
    assert mail.outbox[0].subject.startswith("Новый отзыв 4★: Laura")
    assert mail.outbox[0].reply_to == ["laura@example.com"]
    # hidden from the site until published
    assert "last transfer was long" not in client.get("/").content.decode()


def test_invalid_review_shows_errors(client):
    html = client.post(URL, data(rating="", text="ok")).content.decode()
    assert "Please choose a rating" in html and "at least 20 characters" in html
    assert not Review.objects.exists()


def test_honeypot(client):
    resp = client.post(URL, data(website="http://spam"))
    assert resp.status_code == 302 and not Review.objects.exists()


def test_review_page_and_links(client):
    tour = TourFactory()
    assert "Share your experience" in client.get(f"{URL}?tour={tour.slug}").content.decode()
    assert f"{URL}?tour={tour.slug}" in client.get(tour.get_absolute_url()).content.decode()


def test_highlights_and_thanks_page(client, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        client.post(URL, {**data(rating="2"), "highlights": ["transport", "organisation"]})
    review = Review.objects.get()
    assert review.highlights == "transport,organisation"
    assert "Улучшить: транспорт, организация" in mail.outbox[0].body

    s = SiteSettings.load()
    s.rating_url = "https://g.page/r/example"
    s.save()
    happy = client.get(f"{URL}?sent=1&r=5").content.decode()
    sorry = client.get(f"{URL}?sent=1&r=2").content.decode()
    assert "Review us on Google" in happy and "Review us on Google" not in sorry
    assert "make it right" in sorry
