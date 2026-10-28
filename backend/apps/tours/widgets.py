from django import forms
from django.urls import reverse

from apps.core.maps import map_config


class RouteEditorWidget(forms.Textarea):
    """Map editor (Vue island) for TourDay.waypoints; the JSON lives in a hidden textarea."""

    template_name = "tours/widgets/route_editor.html"
    track = None  # set per form instance, see TourDayAdminForm

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        field_id = context["widget"]["attrs"]["id"]
        context["props_id"] = f"{field_id}-props"
        context["editor_props"] = {
            "map": map_config(),
            "track": self.track,
            "api": {"build": reverse("v1:route-build"), "gpx": reverse("v1:route-gpx")},
            "sourceField": "id_track_source",
            "gpxField": "id_gpx_file",
        }
        return context
