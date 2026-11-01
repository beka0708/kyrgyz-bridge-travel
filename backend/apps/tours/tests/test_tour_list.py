import re

import pytest

from apps.tours.models import TourType
from conftest import TourFactory

pytestmark = pytest.mark.django_db


def card_titles(html):
    """Titles of tour cards only (the request form below also lists every tour)."""
    return re.findall(r'<h3 class="line-clamp-2 text-lg[^"]*">([^<]+)</h3>', html)


def test_list_filters_by_type(client):
    TourFactory(title="Solo trip", tour_type=TourType.SOLO)
    TourFactory(title="Group trip", tour_type=TourType.GROUP)
    TourFactory(title="Hidden trip", is_published=False)

    all_cards = card_titles(client.get("/tours/").content.decode())
    solo_html = client.get("/tours/?type=solo").content.decode()

    assert sorted(all_cards) == ["Group trip", "Solo trip"]
    assert card_titles(solo_html) == ["Solo trip"]
    assert 'aria-current="page"' in solo_html


def test_unknown_type_shows_all(client):
    TourFactory(title="Solo trip", tour_type=TourType.SOLO)
    assert card_titles(client.get("/tours/?type=bogus").content.decode()) == ["Solo trip"]


def test_empty_list_offers_request(client):
    html = client.get("/tours/").content.decode()
    assert "No tours here yet" in html
    assert 'id="inquiry"' in html
