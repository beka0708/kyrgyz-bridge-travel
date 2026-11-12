from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import cache_page

from apps.content.models import FAQ, AboutPhoto, Guide, Review, Stat
from apps.tours.models import Departure, DepartureStatus, Tour, TourType

from .models import SiteSettings, fill_legal
from .seo import PageMeta, absolute, home_meta

HOME_TOURS_LIMIT = 12
HOME_FAQ_LIMIT = 6
HOME_REVIEWS_LIMIT = 12

# One booking story everywhere: ask → we reply with dates and price → deposit → rest on arrival.
STEPS = [
    ("Pick a tour or tell us your idea", "Dates, group size, fitness: roughly is fine."),
    ("We reply {reply_time}", "With free dates and the full price. Asking costs nothing."),
    ("Small deposit, the rest on arrival", "Free cancellation up to 30 days before the start."),
]

# Order matters: the first chip is selected when the page opens.
FILTERS = [
    ("best", "Bestsellers"),
    (TourType.SOLO, "Private tours"),
    (TourType.GROUP, "Group tours"),
    ("all", "All tours"),
]


def _first_cover(tours, tour_type=None):
    for tour in tours:
        if tour.cover and (tour_type is None or tour.tour_type == tour_type):
            return tour.cover
    return None


# Where the photos of the «About us» gallery float on laptops (partials/about/floating.html), in
# order: --x/--y/--w = place and width, --s = drift speed (bigger = faster). Phones show the same
# photos as two sliding strips instead (3 above the text, the rest below).
ABOUT_SLOTS = [
    "--x:4%; --y:6%; --w:19vw; --s:0.35",
    "--x:44%; --y:-3%; --w:9vw; --s:0.12",  # above the text: barely drifts, never crosses it
    "--x:76%; --y:6%; --w:13vw; --s:0.55",
    "--x:6%; --y:44%; --w:12vw; --s:0.6",
    "--x:81%; --y:40%; --w:15vw; --s:0.2",
    "--x:76%; --y:76%; --w:17vw; --s:0.4",
    "--x:10%; --y:82%; --w:11vw; --s:0.75",
]


def about_gallery(site, tours, guides):
    """Photos for the «About us» gallery: the ones uploaded for it, or (until there are any)
    the about photo, guides and tour covers mixed so places and people alternate."""
    photos = [
        (p.image, p.caption) for p in AboutPhoto.objects.published()[: len(ABOUT_SLOTS)] if p.image
    ]
    if not photos:
        # places and people in the order of the slots; whichever runs out, the other fills in
        places = [(img, "") for img in (site.about_image, site.request_image) if img]
        places += [(t.cover, "") for t in tours[1:] + tours[:1] if t.cover]
        people = [(g.photo, g.name) for g in guides if g.photo]
        for kind in ["place", "place", "person", "person", "place", "place", "person"]:
            first, second = (places, people) if kind == "place" else (people, places)
            if first or second:
                photos.append((first or second).pop(0))
    return [
        {"image": image, "caption": caption, "style": slot}
        for (image, caption), slot in zip(photos, ABOUT_SLOTS, strict=False)
    ]


def tour_filters(tours):
    """Chips that change something: a filter matching no tour or every tour is dropped."""
    chips = []
    for value, label in FILTERS:
        count = len(tours) if value == "all" else sum(value in t.filter_tags.split() for t in tours)
        if value == "all" or 0 < count < len(tours):
            chips.append({"value": value, "label": label})
    return chips if len(chips) > 1 else []


def home(request):
    site = SiteSettings.load()
    # bestsellers first: the strongest offer is the first thing a visitor sees
    tours = list(
        Tour.objects.for_cards().order_by("-is_featured", "order", "pk")[:HOME_TOURS_LIMIT]
    )
    reviews = list(Review.objects.published().select_related("tour")[:HOME_REVIEWS_LIMIT])
    faqs = list(FAQ.objects.published()[:HOME_FAQ_LIMIT])
    guides = list(Guide.objects.published())
    featured = [t for t in tours if t.is_featured] or tours[:4]
    filters = tour_filters(tours)
    context = {
        "tours": tours,
        "filters": filters,
        "initial_filter": filters[0]["value"] if filters else "all",
        "reviews": reviews,
        "guides": guides,
        "about_photos": about_gallery(site, tours, guides),
        "faqs": faqs,
        "stats": Stat.objects.published()[:3],
        "steps": [(title.format(reply_time=site.reply_time), text) for title, text in STEPS],
        # Photos fall back to tour covers until the client uploads dedicated ones.
        "hero_image": site.hero_image or _first_cover(featured),
        "about_image": site.about_image or site.hero_image or _first_cover(tours),
        "trust_items": [part.strip() for part in site.trust_line.split("·") if part.strip()],
        "nav_links": [
            {"href": "#tours", "label": "Tours", "icon": "tours"},
            {"href": reverse("tours:dates"), "label": "Dates", "icon": "dates"},
            {"href": "#reviews", "label": "Reviews", "icon": "reviews"},
            {"href": "#guides", "label": "Guides", "icon": "guides"},
            {"href": "#faq", "label": "FAQ", "icon": "faq"},
        ],
        "meta": home_meta(site, _first_cover(featured), faqs),
        "header_cta_href": "#contact",
        "header_cta_label": "Check dates",
    }
    return render(request, "pages/home.html", context)


# Search engines and AI assistants we want to read the site (so they can recommend it).
# A bot with its own group ignores «User-agent: *», so the same rules are repeated for them.
AI_CRAWLERS = [
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "ClaudeBot",
    "Claude-SearchBot",
    "Claude-User",
    "PerplexityBot",
    "Perplexity-User",
    "Google-Extended",
    "Applebot-Extended",
    "Amazonbot",
    "meta-externalagent",
    "DuckAssistBot",
    "MistralAI-User",
    "CCBot",
]


@cache_page(60 * 60)
def robots_txt(request):
    if settings.ROBOTS_DISALLOW_ALL:  # staging / preview servers must not be indexed
        lines = ["User-agent: *", "Disallow: /"]
    else:
        rules = [
            "Allow: /",
            # a custom admin path is a (small) secret: do not advertise it here
            *(["Disallow: /admin/"] if settings.ADMIN_URL == "admin/" else []),
            "Disallow: /api/",
            "Disallow: /inquiry/",
        ]
        lines = [
            "User-agent: *",
            *rules,
            "",
            "# AI assistants and answer engines are welcome",
            *(f"User-agent: {bot}" for bot in AI_CRAWLERS),
            *rules,
            "",
            f"Sitemap: {settings.SITE_URL}/sitemap.xml",
        ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


@cache_page(60 * 15)
def llms_txt(request):
    """llms.txt (llmstxt.org): a plain summary of the agency for AI assistants."""
    site = SiteSettings.load()
    tours = list(Tour.objects.published().order_by("-is_featured", "order", "pk"))
    faqs = FAQ.objects.published()[:HOME_FAQ_LIMIT]
    context = {
        "site": site,
        "tours": tours,
        "departures": Departure.objects.upcoming()
        .exclude(status=DepartureStatus.FULL)
        .select_related("tour")[:24],
        "faqs": faqs,
        "steps": [(title.format(reply_time=site.reply_time), text) for title, text in STEPS],
        "site_url": settings.SITE_URL,
    }
    return render(request, "llms.txt", context, content_type="text/plain; charset=utf-8")


LEGAL_PAGES = {
    "privacy": (
        "Privacy Policy",
        "privacy_policy",
        "How {brand} handles personal data, cookies and analytics.",
    ),
    "terms": ("Terms of Use", "terms_of_use", "Terms of use of the {brand} website."),
}


def legal_page(request, page):
    site = SiteSettings.load()
    title, field, description = LEGAL_PAGES[page]
    meta = PageMeta(
        title=f"{title} — {site.brand_name}",
        description=description.format(brand=site.brand_name),
        canonical=absolute(reverse(f"core:{page}")),
    )
    context = {"meta": meta, "title": title, "text": fill_legal(getattr(site, field), site)}
    return render(request, "pages/legal.html", context)


def privacy(request):
    return legal_page(request, "privacy")


def terms(request):
    return legal_page(request, "terms")


def healthz(request):
    """For Docker/uptime checks: the app answers and the database is reachable."""
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return HttpResponse("db error\n", status=503, content_type="text/plain")
    return HttpResponse("ok\n", content_type="text/plain")
