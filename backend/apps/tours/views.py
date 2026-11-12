from django.db.models import Avg, Count, Prefetch
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from apps.content.models import Review
from apps.core.maps import map_config
from apps.core.models import SiteSettings
from apps.core.seo import tour_list_meta, tour_meta
from apps.stats.services import record_tour_view

from .models import Departure, ListKind, Tour, TourDay, TourType
from .services.departures import by_month

TYPE_FILTERS = [
    ("", "All tours"),
    (TourType.SOLO, "Private"),
    (TourType.GROUP, "Group"),
]


def tour_list(request):
    tours = Tour.objects.for_cards()
    tour_type = request.GET.get("type", "")
    if tour_type not in TourType.values:
        tour_type = ""
    if tour_type:
        tours = tours.filter(tour_type=tour_type)
    filters = [
        {
            "value": value,
            "label": label,
            "active": value == tour_type,
            "query": f"?type={value}" if value else "?",
        }
        for value, label in TYPE_FILTERS
    ]
    label = {TourType.SOLO: "Private tours", TourType.GROUP: "Group tours"}.get(tour_type, "Tours")
    return render(
        request,
        "pages/tour_list.html",
        {
            "tours": tours,
            "tour_type": tour_type,
            "filters": filters,
            "meta": tour_list_meta(SiteSettings.load(), tour_type, label),
        },
    )


def _detail_tabs(tour):
    """Tabs «Included / Not included / What to bring / How to get there»; empty ones are hidden."""
    items = {kind: [] for kind in ListKind}
    for item in tour.list_items.all():
        items[item.kind].append(item.text)
    way = [line.strip(" -•\t") for line in tour.how_to_get_there.splitlines() if line.strip()]
    tabs = [
        ("included", "What's included", "Included in the price", items[ListKind.INCLUDED]),
        ("excluded", "Not included", "Paid separately", items[ListKind.EXCLUDED]),
        ("gear", "What to bring", "Pack this", items[ListKind.GEAR]),
        ("way", "How to get there", "Meeting and return", way),
    ]
    return [
        {"key": key, "label": label, "title": title, "items": values}
        for key, label, title, values in tabs
        if values
    ]


RELATED_LIMIT = 3


def related_tours(tour, limit=RELATED_LIMIT):
    """«You may also like»: same type first, then the rest, featured before others."""
    others = list(
        Tour.objects.for_cards().exclude(pk=tour.pk).order_by("-is_featured", "order", "pk")
    )
    others.sort(key=lambda t: t.tour_type != tour.tour_type)  # stable: keeps the order above
    return others[:limit]


def _price_lists(tour):
    """Included / not included side by side; what to bring and how to get there as accordions."""
    items = {kind: [] for kind in ListKind}
    for item in tour.list_items.all():
        items[item.kind].append(item.text)
    return {
        "included": items[ListKind.INCLUDED],
        "excluded": items[ListKind.EXCLUDED],
        "gear": items[ListKind.GEAR],
        "way": [line.strip(" -•\t") for line in tour.how_to_get_there.splitlines() if line.strip()],
    }


def tour_page_reviews(tour, limit=12):
    """This tour's reviews first, then other guests' words, so the carousel is never thin."""
    own = list(tour.reviews.filter(is_published=True).select_related("tour")[:limit])
    if len(own) < 4:
        others = Review.objects.published().exclude(tour=tour).select_related("tour")
        own += list(others[: limit - len(own)])
    return own


def tour_rating(tour):
    """Average stars of this tour's own published reviews: {"value": 4.8, "count": 6} or None."""
    stats = tour.reviews.filter(is_published=True).aggregate(avg=Avg("rating"), count=Count("pk"))
    if not stats["count"]:
        return None
    return {"value": round(stats["avg"], 1), "count": stats["count"]}


def tour_detail(request, slug):
    # Staff can preview unpublished tours from the admin («Смотреть на сайте»).
    tours = Tour.objects.all() if request.user.is_staff else Tour.objects.published()
    tour = get_object_or_404(
        tours.prefetch_related(
            "images",
            "list_items",
            Prefetch("days", queryset=TourDay.objects.prefetch_related("images")),
        ),
        slug=slug,
    )
    days = list(tour.days.all())
    departures = list(tour.departures.upcoming().select_related("tour"))
    tour.upcoming_departures = departures  # for tour.next_departure_label
    if tour.is_published:
        record_tour_view(request, tour)
    route_props = {
        "map": map_config(),
        "initialDay": days[0].day_number if days else None,
        "showDayChips": False,
        "days": [
            {
                "day_number": day.day_number,
                "title": day.title,
                "waypoints": day.waypoints,
                "track": day.track,
                "track_source": day.track_source,
            }
            for day in days
        ],
    }
    site = SiteSettings.load()
    return render(
        request,
        "pages/tour_detail.html",
        {
            "tour": tour,
            "days": days,
            "tabs": _detail_tabs(tour),
            **_price_lists(tour),
            "gallery": list(tour.images.all()),
            "tour_reviews": tour_page_reviews(tour),
            "tour_rating": tour_rating(tour),
            "departures": departures,
            "departure_months": by_month(departures),
            "related": related_tours(tour),
            "route_props": route_props,
            "meta": tour_meta(site, tour, days),
            "whatsapp_url": site.whatsapp_url(f"Hi! I'm interested in the tour “{tour.title}”."),
            # header (desktop pill nav and phone back link)
            "nav_links": [
                {"href": reverse("tours:list"), "label": "Tours", "icon": "tours"},
                {"href": "#dates", "label": "Dates", "icon": "dates"},
                {"href": "#route", "label": "Route", "icon": "route"},
                {"href": "#included", "label": "What's included", "icon": "included"},
                {"href": "#contact", "label": "Contact", "icon": "contact"},
            ],
            "header_cta_href": "#contact",
            "header_cta_label": "Check dates",
            "back_url": reverse("tours:list"),
        },
    )


def departures_calendar(request):
    """All upcoming dates of all tours, month by month: plan a trip a year ahead."""
    departures = list(
        Departure.objects.upcoming().select_related("tour").order_by("start_date", "tour__order")
    )
    site = SiteSettings.load()
    from apps.core.seo import PageMeta, absolute

    meta = PageMeta(
        title=f"Tour dates in Kyrgyzstan {departures[0].start_date.year if departures else ''}"
        f" — group departures | {site.brand_name}".replace("  ", " "),
        description="Calendar of small-group tours in Kyrgyzstan for the next 12 months: "
        "treks, yurt stays and horse riding. Pick a date and check free seats.",
        canonical=absolute(reverse("tours:dates")),
    )
    return render(
        request,
        "pages/departures.html",
        {
            "months": by_month(departures),
            "departures": departures,
            "meta": meta,
            "back_url": reverse("core:home"),
            "header_cta_href": "#contact",
            "header_cta_label": "Ask about dates",
        },
    )
