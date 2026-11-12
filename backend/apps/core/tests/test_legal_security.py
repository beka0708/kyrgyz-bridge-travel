from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.core.models import SiteSettings
from apps.inquiries.models import Inquiry, InquiryStatus

pytestmark = pytest.mark.django_db


def test_legal_pages_fill_company_details(client):
    s = SiteSettings.load()
    s.legal_name = "Kyrgyz Bridge Travel LLC"
    s.registration_number = "01234567"
    s.legal_address = "Chui Ave 1, Bishkek"
    s.legal_email = "privacy@example.com"
    s.save()

    privacy = client.get("/privacy/").content.decode()
    terms = client.get("/terms/").content.decode()

    assert "Kyrgyz Bridge Travel LLC, registration no. 01234567, Chui Ave 1, Bishkek" in privacy
    assert "privacy@example.com" in privacy and "privacy@example.com" in terms
    assert "no booking or payment is made on this website" in terms
    for page in (privacy, terms):
        assert "{company}" not in page and "{email}" not in page
    assert '/terms/"' in client.get("/").content.decode()  # linked from the footer


def test_csp_header_with_nonce(client):
    resp = client.get("/")
    policy = resp["Content-Security-Policy"]
    nonce = resp.wsgi_request.csp_nonce
    assert f"'nonce-{nonce}'" in policy and "frame-ancestors 'none'" in policy
    assert "object-src 'none'" in policy and "https://tiles.openfreemap.org" in policy
    html = resp.content.decode()
    assert f'<script nonce="{nonce}">' in html
    assert "onclick=" not in html  # inline handlers would be blocked


def test_csp_skips_admin(client, settings):
    assert "Content-Security-Policy" not in client.get(f"/{settings.ADMIN_URL}login/")


def test_purge_personal_data():
    old = timezone.now() - timedelta(days=40)
    keep = Inquiry.objects.create(name="A", email="a@example.com", ip="1.2.3.4", user_agent="x")
    aged = Inquiry.objects.create(name="B", email="b@example.com", ip="1.2.3.4", user_agent="x")
    spam = Inquiry.objects.create(name="C", status=InquiryStatus.SPAM)
    ancient = Inquiry.objects.create(name="D", email="d@example.com")
    Inquiry.objects.filter(pk__in=[aged.pk, spam.pk]).update(created_at=old)
    Inquiry.objects.filter(pk=ancient.pk).update(
        created_at=timezone.now() - timedelta(days=365 * 3 + 5)
    )

    call_command("purge_personal_data")

    keep.refresh_from_db()
    aged.refresh_from_db()
    assert keep.ip == "1.2.3.4"  # fresh: still needed against spam
    assert (aged.ip, aged.user_agent, aged.email) == (None, "", "b@example.com")
    assert not Inquiry.objects.filter(pk__in=[spam.pk, ancient.pk]).exists()


def test_founder_block(client):
    s = SiteSettings.load()
    s.founder_name = "Azamat"
    s.founder_story = "I grew up in Karakol."
    s.founder_since = 2014
    s.save()
    html = client.get("/").content.decode()
    assert 'id="founder"' in html and "Leading trips since" in html
    assert html.index('id="founder"') < html.index('id="guides"') if 'id="guides"' in html else True


def test_cookie_settings_buttons_work_outside_components(client):
    from apps.core.models import SiteSettings

    s = SiteSettings.load()
    s.google_analytics_id = "G-TEST12345"
    s.save()
    html = client.get("/privacy/").content.decode()
    # the delegated handler (lib/analytics.ts) listens for this attribute anywhere on the page
    assert html.count("data-cookie-settings") == 2  # legal page chip + footer


def test_markdown_links_are_safe():
    from apps.core.templatetags.site_tags import simple_markdown

    text = "[ok](/tours/x/) [ext](https://a.org) [bad](javascript:x) [p](//e.com)"
    html = str(simple_markdown(text))
    assert '<a href="/tours/x/">ok</a>' in html
    assert 'href="https://a.org" target="_blank" rel="noopener"' in html
    assert "[bad](javascript:x)" in html and 'href="//e.com"' not in html
