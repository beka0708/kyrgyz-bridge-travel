from django.conf import settings

from .models import SiteSettings


def site_settings(request):
    return {
        "site": SiteSettings.load(),
        "turnstile_site_key": settings.TURNSTILE_SITE_KEY,
        "design_switch": settings.DESIGN_SWITCH,
    }
