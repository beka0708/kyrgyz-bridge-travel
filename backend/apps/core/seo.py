"""Page metadata: <title>, description, canonical, Open Graph and schema.org JSON-LD."""

import json
from dataclasses import dataclass, field

from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from django.utils.text import Truncator

from .images import og_image

# Same escaping as django.utils.html.json_script: JSON inside <script> must not close the tag.
_JSON_SCRIPT_ESCAPES = {ord(">"): "\\u003E", ord("<"): "\\u003C", ord("&"): "\\u0026"}


def absolute(path: str) -> str:
    return path if path.startswith("http") else f"{settings.SITE_URL}{path}"


def logo_url() -> str:
    return absolute(static("brand/logo-512.png"))


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
    # no photo: share the square logo (small card) instead of nothing
    image_size: tuple[int, int] = (1200, 630)

    def __post_init__(self):
        if not self.image:
            self.image, self.image_size = logo_url(), (512, 512)

    @property
    def large_image(self) -> bool:
        return self.image_size[0] > self.image_size[1]

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
    """The agency itself; other blocks point here by @id."""
    data = {
        "@type": "TravelAgency",
        "@id": absolute("/#organization"),
        "name": site.brand_name,
        "url": absolute("/"),
        "logo": {"@type": "ImageObject", "url": logo_url(), "width": 512, "height": 512},
        "description": plain(site.seo_description or site.hero_subtitle, 300),
        "address": {
            "@type": "PostalAddress",
            "addressLocality": "Bishkek",
            "addressCountry": "KG",
            **({"streetAddress": site.address} if site.address else {}),
        },
        "areaServed": {"@type": "Country", "name": "Kyrgyzstan"},
        "knowsAbout": [
            "Tours in Kyrgyzstan",
            "Trekking in the Tian Shan",
            "Yurt stays",
            "Issyk-Kul",
            "Song-Kul",
            "Ala-Kul",
        ],
        "knowsLanguage": ["en", "ru", "ky"],
    }
    if site.legal_name:
        data["legalName"] = site.legal_name
    if site.tagline:
        data["slogan"] = site.tagline
    if site.founder_since:
        data["foundingDate"] = str(site.founder_since)
    if site.founder_name:
        founder = {"@type": "Person", "name": site.founder_name}
        if site.founder_role:
            founder["jobTitle"] = site.founder_role
        photo = social_image(site.founder_photo)
        if photo:
            founder["image"] = photo
        data["founder"] = founder
    if site.phone:
        data["telephone"] = site.phone
    if site.email:
        data["email"] = site.email
    if site.phone or site.email:
        data["contactPoint"] = {
            "@type": "ContactPoint",
            "contactType": "reservations",
            "availableLanguage": ["English", "Russian"],
            **({"telephone": site.phone} if site.phone else {}),
            **({"email": site.email} if site.email else {}),
        }
    image = social_image(site.og_image or site.hero_image)
    data["image"] = image or logo_url()
    same_as = [
        u
        for u in (site.instagram_url, site.facebook_url, site.youtube_url, site.tripadvisor_url)
        if u
    ]
    if site.whatsapp:
        same_as.append(f"https://wa.me/{site.whatsapp}")
    if same_as:
        data["sameAs"] = same_as
    return data


def website(site) -> dict:
    return {
        "@type": "WebSite",
        "@id": absolute("/#website"),
        "name": site.brand_name,
        "url": absolute("/"),
        "inLanguage": "en",
        "publisher": {"@id": absolute("/#organization")},
    }


def faq_page(faqs) -> dict | None:
    faqs = [f for f in faqs if f.question and f.answer]
    if not faqs:
        return None
    return {
        "@type": "FAQPage",
        "@id": absolute("/#faq"),
        "mainEntity": [
            {
                "@type": "Question",
                "name": f.question,
                "acceptedAnswer": {"@type": "Answer", "text": plain(f.answer, 1000)},
            }
            for f in faqs
        ],
    }


def home_meta(site, fallback_image=None, faqs=()) -> PageMeta:
    title = site.seo_title or f"Kyrgyzstan Tours with Local Guides | {site.brand_name}"
    graph = [organization(site), website(site), faq_page(faqs)]
    return PageMeta(
        title=title,
        description=plain(
            site.seo_description
            or "Private and small-group tours in Kyrgyzstan with local guides: Ala-Kul trek, "
            "Song-Kul yurts, Issyk-Kul, canyons. Dates and price within 24 hours."
        ),
        canonical=absolute("/"),
        image=social_image(site.og_image or site.hero_image or fallback_image),
        json_ld=[{"@context": "https://schema.org", "@graph": [b for b in graph if b]}],
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
    }
    if tour.price_from:
        trip["offers"] = {
            "@type": "Offer",
            "price": f"{tour.price_from:.2f}",
            "priceCurrency": tour.currency,
            "url": url,
            "availability": "https://schema.org/InStock",
            "offeredBy": {"@id": absolute("/#organization")},
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
        title=tour.seo_title
        or f"{tour.title} — {tour.duration_days}-day tour in Kyrgyzstan | {site.brand_name}",
        description=plain(tour.seo_description or tour.short_description),
        canonical=url,
        image=image,
        og_type="article",
        json_ld=[trip, breadcrumbs],
    )
