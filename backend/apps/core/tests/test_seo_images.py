import io
import json
import re
from urllib.parse import unquote

import pytest
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image

from apps.core import images
from apps.core.models import SiteSettings
from apps.core.templatetags.site_tags import img
from conftest import TourDayFactory, TourFactory

pytestmark = pytest.mark.django_db


def upload(width, height, name="photo.jpg"):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (120, 160, 90)).save(buf, "JPEG")
    return default_storage.save(f"tests/{name}", ContentFile(buf.getvalue()))


class FieldFileStub:
    def __init__(self, name):
        self.name = name
        self.storage = default_storage

    @property
    def url(self):
        return default_storage.url(self.name)

    def __bool__(self):
        return True


def stub(width, height, name="photo.jpg"):
    return FieldFileStub(upload(width, height, name))


def open_url(url):
    return default_storage.open(unquote(url.removeprefix(settings.MEDIA_URL)))


def test_target_widths_never_upscale():
    assert images.target_widths(3000) == [160, 480, 960, 1600, 2560]
    assert images.target_widths(700) == [160, 480, 700]
    assert images.target_widths(100) == [100]


def test_variants_are_webp_and_resized():
    found = images.variants(stub(2000, 1000))
    assert [v.width for v in found] == [160, 480, 960, 1600, 2000]
    with open_url(found[1].url) as fh:
        variant = Image.open(fh)
        assert variant.format == "WEBP" and variant.size == (480, 240)


def test_og_image_is_1200x630_jpeg():
    url = images.og_image(stub(900, 1400, "tall.jpg"))
    with open_url(url) as fh:
        preview = Image.open(fh)
        assert preview.format == "JPEG" and preview.size == (1200, 630)


def test_broken_upload_falls_back_to_original():
    name = default_storage.save("tests/broken.jpg", ContentFile(b"not an image"))
    found = images.safe_variants(FieldFileStub(name))
    assert found == [images.Variant(default_storage.url(name), 0)]


def test_img_tag_renders_srcset_and_lazy_loading():
    html = str(img(stub(1200, 800), alt='A "lake"', sizes="50vw", css="zoom"))
    assert 'srcset="' in html and "480w" in html and 'sizes="50vw"' in html
    assert 'loading="lazy"' in html and 'class="zoom"' in html
    assert "&quot;lake&quot;" in html
    assert 'fetchpriority="high"' in str(img(stub(1200, 800), priority=True))
    assert img(None) == ""


def ld_blocks(html):
    return [
        json.loads(b)
        for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html)
    ]


def test_tour_page_meta_and_json_ld(client):
    tour = TourFactory(
        title="Ala-Kul </script> Trek", price_from=390, short_description="Lake hike"
    )
    TourDayFactory(tour=tour, day_number=1, title="Karakol")
    html = client.get(tour.get_absolute_url()).content.decode()

    assert f'<link rel="canonical" href="{settings.SITE_URL}/tours/' in html
    assert f'<meta property="og:image" content="{settings.SITE_URL}/media/cache/' in html
    assert "</script> Trek" not in html.split("<body")[0].replace("&lt;/script&gt;", "")
    trip, crumbs = ld_blocks(html)
    assert trip["@type"] == "TouristTrip"
    assert trip["offers"]["price"] == "390.00"
    assert trip["itinerary"]["itemListElement"][0]["item"]["name"] == "Day 1: Karakol"
    assert crumbs["@type"] == "BreadcrumbList"


def test_home_has_travel_agency_ld(client):
    from apps.content.models import FAQ

    s = SiteSettings.load()
    s.phone = "+996 555 000 000"
    s.founder_name = "Zhakshylyk Aitaliev"
    s.save()
    FAQ.objects.create(question="Visa?", answer="<p>Not needed for <b>60 days</b>.</p>")
    (block,) = ld_blocks(client.get("/").content.decode())
    org, site, faq = block["@graph"]
    assert org["@type"] == "TravelAgency" and org["telephone"] == "+996 555 000 000"
    assert org["logo"]["url"].endswith("/static/brand/logo-512.png")
    assert org["founder"]["name"] == "Zhakshylyk Aitaliev"
    assert site["@type"] == "WebSite"
    assert faq["mainEntity"][0]["acceptedAnswer"]["text"] == "Not needed for 60 days."


def test_tour_without_price_has_no_offer(client):
    tour = TourFactory(price_from=0)
    trip, _ = ld_blocks(client.get(tour.get_absolute_url()).content.decode())
    assert "offers" not in trip


def test_page_without_photo_shares_the_logo(client):
    html = client.get("/privacy/").content.decode()
    assert (
        f'<meta property="og:image" content="{settings.SITE_URL}/static/brand/logo-512.png">'
        in html
    )
    assert '<meta name="twitter:card" content="summary">' in html


def test_search_verification_tags(client):
    s = SiteSettings.load()
    s.google_site_verification = "g-code"
    s.bing_site_verification = "b-code"
    s.save()
    html = client.get("/").content.decode()
    assert '<meta name="google-site-verification" content="g-code">' in html
    assert '<meta name="msvalidate.01" content="b-code">' in html


def test_llms_txt(client):
    s = SiteSettings.load()
    s.whatsapp = "996555000000"
    s.save()
    TourFactory(title="Song-Kul & Yurts", slug="song-kul", price_from=320)
    TourFactory(slug="hidden", is_published=False)
    response = client.get("/llms.txt")
    body = response.content.decode()
    assert response["Content-Type"].startswith("text/plain")
    assert body.startswith(f"# {s.brand_name}")
    assert f"[Song-Kul & Yurts]({settings.SITE_URL}/tours/song-kul/)" in body
    assert "from $320" in body and "hidden" not in body
    assert "https://wa.me/996555000000" in body


def test_sitemap_lists_published_tours(client):
    TourFactory(slug="visible")
    TourFactory(slug="hidden", is_published=False)
    xml = client.get("/sitemap.xml").content.decode()
    assert f"{settings.SITE_URL}/tours/visible/" in xml
    assert "hidden" not in xml
    assert f"{settings.SITE_URL}/privacy/" in xml


@pytest.mark.parametrize(
    ("disallow_all", "expected"), [(False, "Disallow: /admin/"), (True, "Disallow: /\n")]
)
def test_robots(client, settings, disallow_all, expected):
    settings.ROBOTS_DISALLOW_ALL = disallow_all
    body = client.get("/robots.txt").content.decode()
    assert expected in body
    assert ("Sitemap:" in body) is not disallow_all
    assert ("User-agent: GPTBot" in body) is not disallow_all


def test_analytics_only_with_ga_id(client):
    assert "googletagmanager" not in client.get("/").content.decode()
    s = SiteSettings.load()
    s.google_analytics_id = "G-TEST123"
    s.save()
    html = client.get("/").content.decode()
    assert "gtag/js?id=G-TEST123" in html
    assert 'analytics_storage: "denied"' in html  # EEA default
    assert 'x-data="cookieBanner"' in html and "Cookie settings" in html
