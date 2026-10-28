import pytest
from django.core import mail
from django.core.management import call_command
from django.urls import reverse

from apps.core.models import SiteSettings
from apps.inquiries.models import Inquiry, InquiryStatus
from conftest import TourFactory

pytestmark = pytest.mark.django_db

URL = "/api/v1/inquiries/"


@pytest.fixture(autouse=True)
def inquiry_email():
    s = SiteSettings.load()
    s.inquiry_email = "agency@example.com"
    s.save()


def payload(**extra):
    return {"name": "Anna", "email": "anna@example.com", "people": 2, **extra}


def test_url_name():
    assert reverse("v1:inquiry-create") == URL


def test_creates_inquiry_and_emails_agency(api, django_capture_on_commit_callbacks):
    tour = TourFactory(title="Ala-Kul")

    with django_capture_on_commit_callbacks(execute=True):
        resp = api.post(URL, payload(tour=tour.slug), format="json")

    assert resp.status_code == 201
    inquiry = Inquiry.objects.get()
    assert inquiry.tour_title == "Ala-Kul"
    assert inquiry.status == InquiryStatus.NEW
    assert inquiry.notified_at is not None
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["agency@example.com"]
    assert "Ala-Kul" in mail.outbox[0].subject


def test_honeypot_marks_spam_without_email(api, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        resp = api.post(URL, payload(website="http://spam"), format="json")

    assert resp.status_code == 201  # same answer as for people
    assert Inquiry.objects.get().status == InquiryStatus.SPAM
    assert mail.outbox == []


def test_rejects_end_date_before_start(api):
    resp = api.post(URL, payload(date_from="2027-07-10", date_to="2027-07-01"), format="json")
    assert resp.status_code == 400
    assert "date_to" in resp.json()


def test_rejects_unpublished_tour(api):
    tour = TourFactory(is_published=False)
    resp = api.post(URL, payload(tour=tour.slug), format="json")
    assert resp.status_code == 400


def test_throttled_after_limit(api, settings):
    for _ in range(5):
        assert api.post(URL, payload(), format="json").status_code == 201
    assert api.post(URL, payload(), format="json").status_code == 429


def test_resend_command_retries_unsent(settings):
    inquiry = Inquiry.objects.create(name="Bob", email="bob@example.com")
    call_command("resend_inquiries")
    inquiry.refresh_from_db()
    assert inquiry.notified_at is not None
    assert len(mail.outbox) == 1
