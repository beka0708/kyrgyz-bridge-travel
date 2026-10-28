from rest_framework.generics import RetrieveAPIView

from apps.core.models import SiteSettings

from .serializers import SiteSettingsSerializer


class SiteSettingsView(RetrieveAPIView):
    """Contacts, messengers and social links shown in the header, footer and buttons."""

    serializer_class = SiteSettingsSerializer

    def get_object(self):
        return SiteSettings.load()
