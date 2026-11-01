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
    message = mail.outbox[0]
    assert message.to == ["agency@example.com"]
    assert message.reply_to == ["anna@example.com"]
    assert message.subject == "Новая заявка: Anna — Ala-Kul, 2 чел."
    assert "Чтобы ответить туристу" in message.body


def test_honeypot_marks_spam_without_email(api, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        resp = api.post(URL, payload(website="http://spam"), format="json")

    assert resp.status_code == 201  # same answer as for people
    assert Inquiry.objects.get().status == InquiryStatus.SPAM
    assert mail.outbox == []


def test_whatsapp_instead_of_email(api, django_capture_on_commit_callbacks):
    data = payload(email="", contact="+996 555 000 000", travel_when="mid-July")
    with django_capture_on_commit_callbacks(execute=True):
        resp = api.post(URL, data, format="json")

    assert resp.status_code == 201
    inquiry = Inquiry.objects.get()
    assert inquiry.travel_when == "mid-July"
    assert mail.outbox[0].reply_to == []
    assert "mid-July" in mail.outbox[0].body


def test_one_field_email_goes_to_email(api, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        resp = api.post(URL, payload(email="", contact="Leo@Example.com"), format="json")

    assert resp.status_code == 201
    inquiry = Inquiry.objects.get()
    assert (inquiry.email, inquiry.contact) == ("Leo@Example.com", "")
    assert mail.outbox[0].reply_to == ["Leo@Example.com"]


def test_one_field_bad_email(api):
    resp = api.post(URL, payload(email="", contact="leo@"), format="json")
    assert resp.status_code == 400
    assert "email" in resp.json()["contact"][0]


def test_needs_email_or_contact(api):
    resp = api.post(URL, payload(email="", contact=""), format="json")
    assert resp.status_code == 400
    assert "contact" in resp.json()


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


@pytest.mark.parametrize(
    ("contact", "link"),
    [
        ("+996 555 123 456", "https://wa.me/996555123456"),
        ("+44 (7700) 900-123", "https://wa.me/447700900123"),
        ("@anna_telegram", ""),
        ("anna@example.com", ""),
        ("123", ""),
    ],
)
def test_whatsapp_link_from_contact(contact, link):
    from apps.inquiries.services import whatsapp_link

    assert whatsapp_link(contact) == link
