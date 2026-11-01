import re

import pytest

from apps.content.models import FAQ, Guide, Review, Season, Stat
from apps.core.models import SiteSettings
from apps.core.templatetags.site_tags import accent_title
from conftest import TourFactory, image_file

pytestmark = pytest.mark.django_db


def test_starred_accent_from_admin():
    html = str(accent_title("Mountains, lakes *and yurts*"))
    assert html == 'Mountains, lakes <span class="text-accent">and yurts</span>'


def test_home_shows_filled_sections(client):
    TourFactory(title="Ala-Kul Trek", is_featured=True)
    TourFactory(title="Song-Kul Nights", is_featured=True)
    Guide.objects.create(name="Aibek", photo=image_file(), quote="I love these hills")
    Review.objects.create(author_name="Anna", text="Great trip")
    FAQ.objects.create(question="Do I need a visa?", answer="No")
    Stat.objects.create(value=3000, suffix="+", label="happy guests")
    Season.objects.create(
        months="June – July", title="Green pastures", text="Yurts", image=image_file()
    )
    s = SiteSettings.load()
    s.hero_title = "Mountains *and yurts*"
    s.whatsapp = "996555000000"
    s.save()

    html = client.get("/").content.decode()

    for section in (
        "tours",
        "reviews",
        "guides",
        "about",
        "seasons",
        "faq",
        "contact",
    ):
        assert f'id="{section}"' in html, section
    assert 'Mountains <span class="text-accent">and yurts</span>' in html
    assert "Aibek" in html
    assert 'id="guide-' in html and "I love these hills" in html  # details dialog
    assert 'data-count="3000"' in html and "3,000</span>+" in html  # counts up, thousands separator
    assert not re.search(r'<h2[^>]*>[^<]*<span class="text-accent">', html)  # one accent: the hero
    assert "https://wa.me/996555000000" in html


def test_home_hides_empty_sections(client):
    html = client.get("/").content.decode()
    assert "marquee" not in html
    for section in ("tours", "seasons", "guides", "reviews", "faq"):
        assert f'id="{section}"' not in html, section
    assert 'id="contact"' in html  # the request form is always there
    assert "on Google" not in html  # no rating until the client enters a real one


def test_rating_and_filters(client):
    TourFactory(title="Day hike", tour_type="solo", duration_days=1)
    TourFactory(title="Big trek", tour_type="group", duration_days=5)
    s = SiteSettings.load()
    s.rating_value = "4.8"
    s.rating_count = 57
    s.save()

    html = client.get("/").content.decode()

    assert "4.8 on Google (57 reviews)" in html
    assert "All · 2" in html and ">1–2 days<" in html
    assert ">Winter<" not in html  # chips without tours are hidden
