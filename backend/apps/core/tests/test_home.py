import re

import pytest

from apps.content.models import FAQ, Feature, Guide, Review, Season, Stat
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
    Feature.objects.create(title="Small groups", text="Up to 8 people")
    Season.objects.create(
        months="June – July", title="Green pastures", text="Yurts", image=image_file()
    )
    s = SiteSettings.load()
    s.hero_title = "Mountains *and yurts*"
    s.whatsapp = "996555000000"
    s.save()

    html = client.get("/").content.decode()

    for section in (
        "formats",
        "tours",
        "seasons",
        "why",
        "about",
        "guides",
        "reviews",
        "faq",
        "inquiry",
    ):
        assert f'id="{section}"' in html, section
    assert 'Mountains <span class="text-accent">and yurts</span>' in html
    assert "I love these hills" in html
    assert 'data-count="3000"' in html and "3,000</span>+" in html  # counts up, thousands separator
    assert not re.search(r'<h2[^>]*>[^<]*<span class="text-accent">', html)  # one accent: the hero
    assert "https://wa.me/996555000000" in html


def test_home_hides_empty_sections(client):
    html = client.get("/").content.decode()
    for section in ("tours", "seasons", "why", "guides", "reviews", "faq", "insta"):
        assert f'id="{section}"' not in html, section
    assert 'id="inquiry"' in html  # the request form is always there
