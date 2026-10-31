"""Page metadata: <title>, description, canonical, Open Graph and schema.org JSON-LD."""

import json
from dataclasses import dataclass, field

from django.conf import settings
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from django.utils.text import Truncator

from .images import og_image

# Same escaping as django.utils.html.json_script: JSON inside <script> must not close the tag.
_JSON_SCRIPT_ESCAPES = {ord(">"): "\\u003E", ord("<"): "\\u003C", ord("&"): "\\u0026"}


def absolute(path: str) -> str:
    return path if path.startswith("http") else f"{settings.SITE_URL}{path}"


def plain(text: str, length: int = 160) -> str:
    """Description-safe text: no markup, no stars, one line, cut at a word."""
    text = " ".join(strip_tags(text or "").replace("*", "").split())
    return Truncator(text).chars(length)


def social_image(fieldfile) -> str:
    if not fieldfile:
        return ""
    try:
        return absolute(og_image(fieldfile))
    except Exception:
        return absolute(fieldfile.url)


@dataclass
class PageMeta:
    title: str
    description: str
    canonical: str
    image: str = ""
    og_type: str = "website"
    json_ld: list[dict] = field(default_factory=list)

    @property
    def json_ld_html(self) -> str:
        blocks = (
            '<script type="application/ld+json">'
            + json.dumps(data, ensure_ascii=False).translate(_JSON_SCRIPT_ESCAPES)
            + "</script>"
            for data in self.json_ld
        )
        return mark_safe("\n".join(blocks))  # noqa: S308 - escaped above


def organization(site) -> dict:
    data = {
        "@type": "TravelAgency",
        "@id": absolute("/#organization"),
        "name": site.brand_name,
        "url": absolute("/"),
        "description": plain(site.seo_description or site.hero_subtitle),
        "address": {
            "@type": "PostalAddress",
            "addressLocality": "Bishkek",
            "addressCountry": "KG",
            **({"streetAddress": site.address} if site.address else {}),
        },
        "areaServed": {"@type": "Country", "name": "Kyrgyzstan"},
    }
    if site.phone:
        data["telephone"] = site.phone
    if site.email:
        data["email"] = site.email
    image = social_image(site.og_image or site.hero_image)
    if image:
        data["image"] = image
    same_as = [
        u
        for u in (site.instagram_url, site.facebook_url, site.youtube_url, site.tripadvisor_url)
        if u
    ]
    if same_as:
        data["sameAs"] = same_as
    return data


def home_meta(site, fallback_image=None) -> PageMeta:
    title = site.seo_title or f"{site.brand_name} — tours in Kyrgyzstan"
    return PageMeta(
        title=title,
        description=plain(site.seo_description or site.hero_subtitle),
        canonical=absolute("/"),
        image=social_image(site.og_image or site.hero_image or fallback_image),
        json_ld=[{"@context": "https://schema.org", **organization(site)}],
    )


def tour_list_meta(site, tour_type: str, label: str) -> PageMeta:
    path = reverse("tours:list") + (f"?type={tour_type}" if tour_type else "")
    return PageMeta(
        title=f"{label} in Kyrgyzstan — {site.brand_name}",
        description=plain(
            {"solo": site.solo_text, "group": site.group_text}.get(tour_type)
            or "Private and group tours across Kyrgyzstan with local guides: "
            "mountain lakes, treks, yurts and canyons."
        ),
        canonical=absolute(path),
        image=social_image(site.og_image or site.hero_image),
    )


def tour_meta(site, tour, days) -> PageMeta:
    url = absolute(tour.get_absolute_url())
    image = social_image(tour.og_image or tour.cover)
    trip = {
        "@context": "https://schema.org",
        "@type": "TouristTrip",
        "name": tour.title,
        "description": plain(tour.description or tour.short_description, 500),
        "url": url,
        "touristType": tour.type_label,
        "provider": {
            "@type": "TravelAgency",
            "@id": absolute("/#organization"),
            "name": site.brand_name,
        },
        "offers": {
            "@type": "Offer",
            "price": f"{tour.price_from:.2f}",
            "priceCurrency": tour.currency,
            "url": url,
            "availability": "https://schema.org/InStock",
        },
    }
    if image:
        trip["image"] = image
    if days:
        trip["itinerary"] = {
            "@type": "ItemList",
            "numberOfItems": len(days),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": day.day_number,
                    "item": {
                        "@type": "TouristAttraction",
                        "name": f"Day {day.day_number}: {day.title}",
                        **({"description": plain(day.description, 300)} if day.description else {}),
                    },
                }
                for day in days
            ],
        }
    breadcrumbs = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": absolute("/")},
            {
                "@type": "ListItem",
                "position": 2,
                "name": "Tours",
                "item": absolute(reverse("tours:list")),
            },
            {"@type": "ListItem", "position": 3, "name": tour.title, "item": url},
        ],
    }
    return PageMeta(
        title=tour.seo_title or f"{tour.title} — {tour.duration_days}-day tour | {site.brand_name}",
        description=plain(tour.seo_description or tour.short_description),
        canonical=url,
        image=image,
        og_type="article",
        json_ld=[trip, breadcrumbs],
    )
