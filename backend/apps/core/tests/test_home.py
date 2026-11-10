import re

import pytest

from apps.content.models import FAQ, Guide, Review, Stat
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
    s = SiteSettings.load()
    s.hero_title = "Mountains *and yurts*"
    s.whatsapp = "996555000000"
    s.save()

    html = client.get("/").content.decode()

    order = ["tours", "reviews", "about", "how", "guides", "faq", "contact"]
    positions = [html.index(f'id="{section}"') for section in order]
    assert positions == sorted(positions)  # guides come after «about»
    assert 'id="seasons"' not in html
    assert 'Mountains <span class="text-accent">and yurts</span>' in html
    assert "Aibek" in html
    assert 'id="guide-' in html and "I love these hills" in html  # details dialog
    # counts up, thousands separator, the suffix in the accent colour
    assert 'data-count="3000"' in html and '3,000</span><span class="text-accent">+</span>' in html
    assert not re.search(r'<h2[^>]*>[^<]*<span class="text-accent">', html)  # one accent: the hero
    assert "https://wa.me/996555000000" in html


def test_home_hides_empty_sections(client):
    html = client.get("/").content.decode()
    assert "marquee" not in html
    for section in ("tours", "guides", "reviews", "faq"):
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


def test_tour_card_badges(client):
    hit = TourFactory(title="Lake trek", is_featured=True, max_altitude_m=3920)
    TourFactory(title="Day hike", is_featured=False)
    Review.objects.create(author_name="Anna", text="Great", rating=5, tour=hit)
    Review.objects.create(author_name="Hidden", text="Meh", rating=1, tour=hit, is_published=False)

    html = client.get("/").content.decode()

    assert html.count("Bestseller") >= 1
    assert "↑ 3,920 m" in html
    cards = html.split('id="tours"', 1)[1].split('id="reviews"', 1)[0]
    assert (
        "1 review" not in cards and "Challenging" not in cards
    )  # no rating or difficulty on cards
    assert html.index("Lake trek") < html.index("Day hike")  # bestsellers first


def test_classic_design_is_gone(client):
    assert client.get("/classic/").status_code == 404
    assert "Design version" not in client.get("/").content.decode()


def test_phone_menu_is_outside_the_blurred_header(client):
    html = client.get("/").content.decode()
    assert 'x-teleport="body"' in html  # backdrop-filter would clip a fixed menu inside the header
    assert "lang_switch" not in html and "Русский" not in html  # no language switch
    assert "t.me/" not in html  # Telegram removed
