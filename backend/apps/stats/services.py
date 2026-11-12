import re

from django.core.cache import cache
from django.db.models import F
from django.utils import timezone

from apps.inquiries.services import client_ip

from .geo import country_for_ip
from .models import ContactClick, CountryVisit, TourView

BOT_UA = re.compile(r"bot|crawl|spider|slurp|preview|facebookexternalhit|headless|lighthouse", re.I)


def is_counted(request) -> bool:
    """Real visitors only: no bots, no link previews, no prefetch, no staff browsing the site."""
    if request.user.is_authenticated and request.user.is_staff:
        return False
    if request.headers.get("Sec-Purpose", "").startswith("prefetch"):
        return False
    return not BOT_UA.search(request.headers.get("User-Agent", "") or "bot")


def _first_time_today(kind: str, request, key: str) -> bool:
    """One count per visitor (IP) per day; the IP itself is never stored, only a cache key."""
    day = timezone.localdate()
    return cache.add(f"stats:{kind}:{day}:{key}:{client_ip(request)}", 1, 60 * 60 * 26)


def record_tour_view(request, tour) -> None:
    if not is_counted(request) or not _first_time_today("tour", request, str(tour.pk)):
        return
    day = timezone.localdate()
    row, _ = TourView.objects.get_or_create(tour=tour, date=day)
    TourView.objects.filter(pk=row.pk).update(views=F("views") + 1)


def record_click(request, channel: str) -> None:
    if not is_counted(request) or not _first_time_today("click", request, channel):
        return
    day = timezone.localdate()
    row, _ = ContactClick.objects.get_or_create(date=day, channel=channel)
    ContactClick.objects.filter(pk=row.pk).update(clicks=F("clicks") + 1)


def record_visit(request) -> None:
    """One visitor per day, by country (dashboard «Откуда заходят»)."""
    if not is_counted(request) or not _first_time_today("visit", request, "site"):
        return
    day = timezone.localdate()
    country = country_for_ip(client_ip(request))
    row, _ = CountryVisit.objects.get_or_create(date=day, country=country)
    CountryVisit.objects.filter(pk=row.pk).update(visits=F("visits") + 1)
