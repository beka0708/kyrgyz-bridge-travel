"""Classic home (design-v1), kept at /classic/ so the client can compare it with the new one.

Delete this module, its URL and templates/classic/ once a design is chosen.
"""

from django.conf import settings
from django.http import Http404
from django.shortcuts import render

from apps.content.models import FAQ, Feature, GalleryPost, Guide, Partner, Review, Season, Stat
from apps.tours.models import Tour, TourType

from .models import SiteSettings
from .seo import home_meta

HOME_TOURS_LIMIT = 8

# One booking story everywhere: ask → we reply with dates and price → deposit → rest on arrival.
STEPS = [
    (
        "Choose a tour or tell us your idea",
        "Pick a tour, or tell us your dates, group and fitness.",
    ),
    (
        "Send a request or message us",
        "We reply {reply_time} with available dates and the full price.",
    ),
    (
        "Confirm with a deposit",
        "Pay the rest when you arrive. Free cancellation up to 30 days before.",
    ),
]


def _first_cover(tours, tour_type=None):
    for tour in tours:
        if tour.cover and (tour_type is None or tour.tour_type == tour_type):
            return tour.cover
    return None


def _format_facts(tours, tour_type):
    """«4 tours · from $79» for the private/group cards."""
    of_type = [t for t in tours if t.tour_type == tour_type]
    if not of_type:
        return ""
    cheapest = min(of_type, key=lambda t: t.price_from)
    count = f"{len(of_type)} tour{'' if len(of_type) == 1 else 's'}"
    return f"{count} · {cheapest.price_display}" if cheapest.price_from else count


def home_classic(request):
    if not settings.DESIGN_SWITCH:
        raise Http404
    site = SiteSettings.load()
    all_tours = list(Tour.objects.published())
    tours = all_tours[:HOME_TOURS_LIMIT]
    featured = [t for t in tours if t.is_featured] or tours[:4]
    reviews = list(Review.objects.published().select_related("tour")[:6])
    partners = list(Partner.objects.published())
    gallery_posts = list(GalleryPost.objects.published()[:8])

    context = {
        "tours": tours,
        "seasons": Season.objects.published().select_related("tour"),
        "features": Feature.objects.published(),
        "guides": Guide.objects.published(),
        "reviews": reviews,
        "faqs": FAQ.objects.published(),
        # Thin sections look abandoned: show them only when there is enough to show.
        "partners": partners if len(partners) >= 3 else [],
        "gallery_posts": gallery_posts if len(gallery_posts) >= 6 else [],
        "stats": Stat.objects.published()[:3],
        "steps": [(title, text.format(reply_time=site.reply_time)) for title, text in STEPS],
        # Photos fall back to tour covers until the client uploads dedicated ones.
        "hero_image": site.hero_image or _first_cover(featured),
        "solo_image": site.solo_image or _first_cover(tours, TourType.SOLO),
        "group_image": site.group_image or _first_cover(tours, TourType.GROUP),
        "about_image": site.about_image or site.hero_image or _first_cover(tours),
        "steps_image": site.steps_image or _first_cover(tours[3:]),
        "faq_image": site.faq_image or _first_cover(tours[5:]),
        "request_image": site.request_image or _first_cover(tours[1:]),
        "solo_facts": _format_facts(all_tours, TourType.SOLO),
        "group_facts": _format_facts(all_tours, TourType.GROUP),
        "min_price": min(
            (t for t in all_tours if t.price_from), key=lambda t: t.price_from, default=None
        ),
        "tour_filter_options": [
            ("all", "All"),
            (TourType.SOLO, "Private"),
            (TourType.GROUP, "Group"),
        ],
        "nav_links": [
            {"href": "#tours", "label": "Tours"},
            {"href": "#seasons", "label": "When to go"},
            {"href": "#reviews" if reviews else "#faq", "label": "Reviews" if reviews else "FAQ"},
            {"href": "#faq", "label": "FAQ"},
        ],
        "meta": home_meta(site, _first_cover(featured)),
        "header_cta_href": "#inquiry",
        "header_cta_label": "Check dates",
    }
    return render(request, "classic/home.html", context)
