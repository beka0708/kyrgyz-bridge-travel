from decimal import Decimal

import pytest

from apps.core.templatetags.site_tags import accent_title
from apps.tours.models import Currency, Difficulty, ListKind, TourType
from conftest import TourDayFactory, TourFactory


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Ala-Kul: hike to the lake", 'Ala-Kul: <span class="text-accent">hike to the lake</span>'),
        ("Song-Kul Nights", 'Song-Kul <span class="text-accent">Nights</span>'),
        ("Arslanbob", "Arslanbob"),
        ("<b>x</b> y", '&lt;b&gt;x&lt;/b&gt; <span class="text-accent">y</span>'),
    ],
)
def test_accent_title(title, expected):
    assert str(accent_title(title)) == expected


def test_public_labels_are_english():
    tour = TourFactory.build(
        tour_type=TourType.SOLO,
        difficulty=Difficulty.HARD,
        group_size_max=8,
        price_from=Decimal("1390"),
        currency=Currency.USD,
    )
    assert tour.type_label == "Private tour"
    assert tour.difficulty_label == "Challenging"
    assert tour.group_label == "up to 8 people"
    assert tour.price_label == "$1,390"
    tour.currency = Currency.KGS
    assert tour.price_label == "1,390 KGS"


@pytest.mark.django_db
def test_day_meta_label():
    day = TourDayFactory(distance_km=Decimal("12.5"), ascent_m=1200, travel_time="5–6 h")
    # non-breaking spaces keep numbers and units together; thousands separator for metres
    assert day.meta_label == "12.5\u00a0km · ↑\u00a01,200\u00a0m · 5–6 h"


@pytest.mark.django_db
def test_tour_page_renders_sections(client):
    day = TourDayFactory(
        tour__title="Ala-Kul: hike", tour__how_to_get_there="Meet in Bishkek\nTransfer"
    )
    day.tour.list_items.create(kind=ListKind.GEAR, text="Boots")

    html = client.get(day.tour.get_absolute_url()).content.decode()

    assert 'id="program"' in html
    assert "What to bring" in html and "Boots" in html
    assert "How to get there" in html and "Transfer" in html
    assert "Not included" not in html  # empty tabs are hidden
    assert '<span class="text-accent">hike</span>' in html


@pytest.mark.django_db
def test_related_tours_same_type_first(client):
    from apps.tours.views import related_tours

    tour = TourFactory(title="Main", tour_type=TourType.GROUP)
    solo = TourFactory(title="Solo", tour_type=TourType.SOLO, is_featured=True)
    group = TourFactory(title="Group", tour_type=TourType.GROUP)
    TourFactory(title="Hidden", tour_type=TourType.GROUP, is_published=False)

    assert related_tours(tour) == [group, solo]
    html = client.get(tour.get_absolute_url()).content.decode()
    assert 'id="more-tours"' in html and "You may also like" in html
