import pytest
from django.core import mail

from apps.core.models import SiteSettings
from apps.inquiries.models import Inquiry, InquiryStatus
from conftest import TourFactory

pytestmark = pytest.mark.django_db

URL = "/inquiry/"


@pytest.fixture(autouse=True)
def inquiry_email():
    s = SiteSettings.load()
    s.inquiry_email = "agency@example.com"
    s.save()


def post(client, **extra):
    data = {"name": "Anna", "email": "anna@example.com", "people": "2", "next": "/tours/", **extra}
    return client.post(URL, data)


def test_success_redirects_back_with_thanks(client, django_capture_on_commit_callbacks):
    tour = TourFactory()
    with django_capture_on_commit_callbacks(execute=True):
        resp = post(client, tour=tour.slug, next=tour.get_absolute_url())
    assert resp.status_code == 302
    assert resp["Location"] == f"{tour.get_absolute_url()}?sent=1#inquiry"
    assert Inquiry.objects.get().tour == tour
    assert len(mail.outbox) == 1


def test_thanks_message_after_redirect(client):
    html = client.get("/tours/?sent=1").content.decode()
    assert "Request received" in html


def test_honeypot_saves_as_spam_silently(client, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        resp = post(client, website="http://spam")
    assert resp.status_code == 302
    assert Inquiry.objects.get().status == InquiryStatus.SPAM
    assert mail.outbox == []


def test_invalid_form_shows_errors(client):
    resp = post(client, email="not-an-email", date_from="2027-07-10", date_to="2027-07-01")
    assert resp.status_code == 400
    html = resp.content.decode()
    assert "Email" in html and "End date is before start date." in html
    assert not Inquiry.objects.exists()


def test_rate_limit(client):
    for _ in range(5):
        assert post(client).status_code == 302
    resp = post(client)
    assert resp.status_code == 400
    assert "Too many requests" in resp.content.decode()


def test_external_next_is_ignored(client):
    resp = post(client, next="https://evil.example.com/")
    assert resp["Location"] == "/?sent=1#inquiry"


def test_get_not_allowed(client):
    assert client.get(URL).status_code == 405
