from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.tours.models import Tour


class SiteUrlSitemap(Sitemap):
    """Use SITE_URL for the domain, so sitemap links match canonical URLs behind a proxy."""

    @property
    def protocol(self):
        return urlsplit(settings.SITE_URL).scheme

    def get_domain(self, site=None):
        return urlsplit(settings.SITE_URL).netloc


class StaticSitemap(SiteUrlSitemap):
    changefreq = "weekly"

    def items(self):
        return [
            ("core:home", "", 1.0),
            ("tours:list", "", 0.8),
            ("tours:list", "?type=solo", 0.6),
            ("tours:list", "?type=group", 0.6),
            ("tours:dates", "", 0.7),
            ("core:privacy", "", 0.2),
            ("core:terms", "", 0.2),
        ]

    def location(self, item):
        name, query, _ = item
        return reverse(name) + query

    def priority(self, item):
        return item[2]


class TourSitemap(SiteUrlSitemap):
    changefreq = "monthly"
    priority = 0.9

    def items(self):
        return Tour.objects.published().only("slug", "updated_at")

    def lastmod(self, tour):
        return tour.updated_at


SITEMAPS = {"pages": StaticSitemap, "tours": TourSitemap}
