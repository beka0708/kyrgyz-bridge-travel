import io

import factory
import pytest
from django.core.files.base import ContentFile
from PIL import Image
from rest_framework.test import APIClient

from apps.tours.models import Difficulty, Tour, TourDay, TourType


def image_file(name="test.jpg"):
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), (200, 100, 50)).save(buf, "JPEG")
    return ContentFile(buf.getvalue(), name=name)


class TourFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tour

    title = factory.Sequence(lambda n: f"Tour {n}")
    slug = factory.Sequence(lambda n: f"tour-{n}")
    tour_type = TourType.GROUP
    short_description = "Short"
    price_from = 300
    duration_days = 3
    difficulty = Difficulty.MODERATE
    cover = factory.LazyFunction(image_file)


class TourDayFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TourDay

    tour = factory.SubFactory(TourFactory)
    day_number = factory.Sequence(lambda n: n + 1)
    title = "Day"
    waypoints = factory.LazyFunction(
        lambda: [{"lat": 42.87, "lng": 74.57}, {"lat": 42.49, "lng": 78.39}]
    )


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture(autouse=True)
def _clear_cache():
    from django.core.cache import cache

    cache.clear()
