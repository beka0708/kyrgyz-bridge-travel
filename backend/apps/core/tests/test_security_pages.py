import pytest
from django.contrib.auth.models import User
from django.test import RequestFactory
from django.views.defaults import server_error

from apps.core.models import SiteSettings
from apps.core.templatetags.site_tags import simple_markdown

pytestmark = pytest.mark.django_db


def test_custom_404_page(client):
    resp = client.get("/no-such-page/")
    assert resp.status_code == 404
    assert "Lost on the" in resp.content.decode()


def test_500_page_is_self_contained():
    resp = server_error(RequestFactory().get("/"))
    html = resp.content.decode()
    assert resp.status_code == 500
    assert "Something went" in html and "<style>" in html
    assert "/static/" not in html  # no built assets that could be broken too


def test_privacy_page_from_admin_text(client):
    s = SiteSettings.load()
    s.privacy_policy = "## Data\n- **Email** for replies\n<script>alert(1)</script>"
    s.save()
    html = client.get("/privacy/").content.decode()
    assert "<h2>Data</h2>" in html
    assert "<li><strong>Email</strong> for replies</li>" in html
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_default_privacy_policy_is_filled():
    text = SiteSettings.load().privacy_policy
    assert "## Your rights" in text and "Google Analytics" in text


def test_simple_markdown_lists_close_before_headings():
    html = simple_markdown("- a\n- b\n## Next\ntext")
    assert html == "<ul><li>a</li><li>b</li></ul>\n<h2>Next</h2>\n<p>text</p>"


def test_footer_links_to_privacy(client):
    assert 'href="/privacy/"' in client.get("/").content.decode()


def test_admin_locks_after_five_wrong_passwords(client):
    User.objects.create_superuser("boss", "boss@example.com", "correct-horse-battery")
    url = "/admin/login/?next=/admin/"
    for _ in range(5):
        client.post(url, {"username": "boss", "password": "wrong"})
    locked = client.post(url, {"username": "boss", "password": "correct-horse-battery"})
    assert locked.status_code == 429
    assert not client.get("/admin/").wsgi_request.user.is_authenticated


def test_healthz(client):
    resp = client.get("/healthz/")
    assert resp.status_code == 200 and resp.content == b"ok\n"
