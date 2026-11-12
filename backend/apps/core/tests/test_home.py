import re

import pytest

from apps.content.models import FAQ, AboutPhoto, Guide, Review, Stat
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
    # accents: the hero and the «About us» title only
    accented = re.findall(r'<h2([^>]*)>[^<]*<span class="text-accent">', html)
    assert all("about-float__title" in attrs for attrs in accented)
    assert "https://wa.me/996555000000" in html


def test_home_hides_empty_sections(client):
    html = client.get("/").content.decode()
    assert "marquee" not in html
    for section in ("tours", "guides", "reviews", "faq"):
        assert f'id="{section}"' not in html, section
    assert 'id="contact"' in html  # the request form is always there
    assert "on Google" not in html  # no rating until the client enters a real one


def test_rating_and_filters(client):
    TourFactory(title="Day hike", tour_type="solo", duration_days=1, is_featured=True)
    TourFactory(title="Big trek", tour_type="group", duration_days=5)
    s = SiteSettings.load()
    s.rating_value = "4.8"
    s.rating_count = 57
    s.save()

    html = client.get("/").content.decode()

    assert "4.8 on Google (57 reviews)" in html
    # order: bestsellers first (selected), then private, group, all — no counts
    chips = re.findall(r'class="chip"[^>]*>([^<]+)</button>', html)
    assert chips == ["Bestsellers", "Private tours", "Group tours", "All tours"]
    assert "tourFilter('best')" in html
    # the non-featured tour is hidden until Alpine starts (no flash of all tours)
    assert html.count('style="display: none"') >= 2


def test_filters_without_bestsellers_start_with_private(client):
    TourFactory(tour_type="solo")
    TourFactory(tour_type="group")
    html = client.get("/").content.decode()
    chips = re.findall(r'class="chip"[^>]*>([^<]+)</button>', html)
    assert chips == ["Private tours", "Group tours", "All tours"]


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


def test_reviews_show_up_to_twelve(client):
    for i in range(14):
        Review.objects.create(author_name=f"Guest {i}", text="Great", rating=5)
    html = client.get("/").content.decode()
    assert "reviewSpotlight" in html
    assert html.count('aria-roledescription="slide"') == 12


def test_about_gallery_falls_back_to_guides_and_tours(client):
    Stat.objects.create(value=12, suffix="+", label="years")
    TourFactory(title="Ala-Kul Trek")
    Guide.objects.create(name="Aibek", photo=image_file())
    html = client.get("/").content.decode()
    assert 'id="about" class="about-float' in html and 'data-about-scene="floating"' in html
    assert 'data-count="12"' in html
    assert "<figcaption>Aibek</figcaption>" in html  # guides are captioned with their names
    assert html.count('<figure class="about-float__ph') == 2  # one tour cover + one guide


def test_about_gallery_and_texts_come_from_the_admin(client):
    for i in range(9):
        AboutPhoto.objects.create(image=image_file(), caption=f"Photo {i}")
    AboutPhoto.objects.create(image=image_file(), caption="Hidden", is_published=False)
    s = SiteSettings.load()
    s.about_eyebrow = "Our people"
    s.about_link_label = "See who leads"
    s.founder_since = 2014
    s.save()
    Guide.objects.create(name="Aibek", photo=image_file())

    html = client.get("/").content.decode()
    assert html.count('<figure class="about-float__ph') == 7  # one per place in the layout
    assert "Photo 0" in html and "Photo 7" not in html and "Hidden" not in html
    assert "Since 2014 · Our people" in html
    assert "See who leads" in html


def test_footer_shows_only_filled_social_links(client):
    s = SiteSettings.load()
    s.instagram_url = "https://instagram.com/kgtours"
    s.tiktok_url = "https://tiktok.com/@kgtours"
    s.save()
    html = client.get("/").content.decode()
    assert 'aria-label="Instagram"' in html and 'aria-label="TikTok"' in html
    assert 'aria-label="Facebook"' not in html and 'aria-label="Tripadvisor"' not in html


@pytest.mark.parametrize(
    ("query", "marker"),
    [("", "reviewSpotlight")],
)  # fmt: skip
def test_review_designs_to_compare(client, query, marker):
    Review.objects.create(author_name="Anna", text="Great trip")
    html = client.get(f"/{query}").content.decode()
    assert marker in html and 'id="reviews"' in html


def test_review_star_link_opens_the_form_with_that_rating(client):
    Review.objects.create(author_name="Anna", text="Great trip", photo=image_file())
    html = client.get("/").content.decode()
    assert "/reviews/new/?rating=5" in html
    form = client.get("/reviews/new/?rating=4").content.decode()
    assert "rating: 4" in form
    assert "rating: 0" in client.get("/reviews/new/?rating=9").content.decode()
    # guest photos show in the faces (a block, so the round frame gets its size)
    assert '<span class="pic block size-10' in html


def test_no_template_comment_leaks_into_the_page(client):
    Review.objects.create(author_name="Anna", text="Great trip")
    for query in ("",):
        html = client.get(f"/{query}").content.decode()
        assert "{#" not in html and "#}" not in html and "{%" not in html
