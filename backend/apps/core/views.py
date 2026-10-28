from django.shortcuts import render

from apps.content.models import FAQ, GalleryPost, Guide, Partner, Review, Stat
from apps.tours.models import Tour, TourType

from .models import SiteSettings

HOME_TOURS_LIMIT = 8

STEPS = [
    (
        "Pick a tour or tell us your wishes",
        "Open a tour page or simply describe what you'd like to see.",
    ),
    (
        "Message us on WhatsApp or Telegram",
        "The tour name is added to the message automatically — just press send.",
    ),
    (
        "Agree on the details and go",
        "Dates, group and programme — we settle everything in the chat.",
    ),
]


def _first_cover(tours, tour_type=None):
    for tour in tours:
        if tour.cover and (tour_type is None or tour.tour_type == tour_type):
            return tour.cover
    return None


def home(request):
    site = SiteSettings.load()
    tours = list(Tour.objects.published()[:HOME_TOURS_LIMIT])
    featured = [t for t in tours if t.is_featured] or tours[:4]
    reviews = Review.objects.published().select_related("tour")[:6]

    context = {
        "tours": tours,
        "featured": featured,
        "guides": Guide.objects.published(),
        "reviews": reviews,
        "faqs": FAQ.objects.published(),
        "partners": Partner.objects.published(),
        "gallery_posts": GalleryPost.objects.published()[:6],
        "stats": Stat.objects.published()[:3],
        # Photos fall back to tour covers until the client uploads dedicated ones.
        "hero_image": site.hero_image or _first_cover(featured),
        "solo_image": site.solo_image or _first_cover(tours, TourType.SOLO),
        "group_image": site.group_image or _first_cover(tours, TourType.GROUP),
        "about_image": site.about_image or site.hero_image or _first_cover(tours),
        "tour_filter_options": [
            ("all", "All"),
            (TourType.SOLO, "Private"),
            (TourType.GROUP, "Group"),
        ],
        "steps": STEPS,
        "nav_links": [
            {"href": "#tours", "label": "Tours"},
            {"href": "#why", "label": "About"},
            {"href": "#reviews" if reviews else "#faq", "label": "Reviews" if reviews else "FAQ"},
            {"href": "#contact", "label": "Contacts"},
        ],
        "header_cta_href": "#contact",
        "header_cta_label": "Message us",
    }
    return render(request, "pages/home.html", context)
