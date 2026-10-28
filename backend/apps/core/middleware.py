from django.conf import settings
from django.utils import translation


class AdminLocaleMiddleware:
    """The public site is English, but the client works in the admin in Russian."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin/"):
            translation.activate(settings.ADMIN_LANGUAGE_CODE)
            request.LANGUAGE_CODE = settings.ADMIN_LANGUAGE_CODE
        response = self.get_response(request)
        translation.deactivate()
        return response
