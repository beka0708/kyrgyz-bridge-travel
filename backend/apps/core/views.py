from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import cache_page

from apps.content.models import FAQ, Guide, Review, Stat
from apps.tours.models import Tour, TourType

from .models import SiteSettings
from .seo import PageMeta, absolute, home_meta

HOME_TOURS_LIMIT = 12
HOME_FAQ_LIMIT = 6

# One booking story everywhere: ask → we reply with dates and price → deposit → rest on arrival.
STEPS = [
    ("Pick a tour or tell us your idea", "Dates, group size, fitness: roughly is fine."),
    ("We reply {reply_time}", "With free dates and the full price. Asking costs nothing."),
    ("Small deposit, the rest on arrival", "Free cancellation up to 30 days before the start."),
]

FILTERS = [
    ("all", "All"),
    (TourType.SOLO, "Private"),
    (TourType.GROUP, "Small group"),
    ("short", "1–2 days"),
    ("winter", "Winter"),
]


def _first_cover(tours, tour_type=None):
    for tour in tours:
        if tour.cover and (tour_type is None or tour.tour_type == tour_type):
            return tour.cover
    return None


def tour_filters(tours):
    """Chips with at least one tour; «All» carries the total («All · 8»)."""
    chips = []
    for value, label in FILTERS:
        count = len(tours) if value == "all" else sum(value in t.filter_tags.split() for t in tours)
        if count and (value == "all" or count < len(tours)):
            chips.append(
                {"value": value, "label": f"{label} · {count}" if value == "all" else label}
            )
    return chips if len(chips) > 1 else []


def home(request):
    site = SiteSettings.load()
    # bestsellers first: the strongest offer is the first thing a visitor sees
    tours = list(
        Tour.objects.for_cards().order_by("-is_featured", "order", "pk")[:HOME_TOURS_LIMIT]
    )
    reviews = list(Review.objects.published().select_related("tour")[:3])
    featured = [t for t in tours if t.is_featured] or tours[:4]
    context = {
        "tours": tours,
        "filters": tour_filters(tours),
        "reviews": reviews,
        "guides": Guide.objects.published(),
        "faqs": FAQ.objects.published()[:HOME_FAQ_LIMIT],
        "stats": Stat.objects.published()[:3],
        "steps": [(title.format(reply_time=site.reply_time), text) for title, text in STEPS],
        # Photos fall back to tour covers until the client uploads dedicated ones.
        "hero_image": site.hero_image or _first_cover(featured),
        "about_image": site.about_image or site.hero_image or _first_cover(tours),
        "trust_items": [part.strip() for part in site.trust_line.split("·") if part.strip()],
        "nav_links": [
            {"href": "#tours", "label": "Tours"},
            {"href": "#reviews", "label": "Reviews"},
            {"href": "#guides", "label": "Guides"},
            {"href": "#faq", "label": "FAQ"},
        ],
        "meta": home_meta(site, _first_cover(featured)),
        "header_cta_href": "#contact",
        "header_cta_label": "Check dates",
    }
    return render(request, "pages/home.html", context)


@cache_page(60 * 60)
def robots_txt(request):
    if settings.ROBOTS_DISALLOW_ALL:  # staging / preview servers must not be indexed
        lines = ["User-agent: *", "Disallow: /"]
    else:
        lines = [
            "User-agent: *",
            # a custom admin path is a (small) secret: do not advertise it here
            *(["Disallow: /admin/"] if settings.ADMIN_URL == "admin/" else []),
            "Disallow: /api/",
            "Disallow: /inquiry/",
            "",
            f"Sitemap: {settings.SITE_URL}/sitemap.xml",
        ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def privacy(request):
    site = SiteSettings.load()
    meta = PageMeta(
        title=f"Privacy Policy — {site.brand_name}",
        description=f"How {site.brand_name} handles personal data, cookies and analytics.",
        canonical=absolute(reverse("core:privacy")),
    )
    return render(request, "pages/privacy.html", {"meta": meta})


def healthz(request):
    """For Docker/uptime checks: the app answers and the database is reachable."""
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return HttpResponse("db error\n", status=503, content_type="text/plain")
    return HttpResponse("ok\n", content_type="text/plain")
