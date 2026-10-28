from django import forms

from .models import TourDay
from .services.errors import RoutingError
from .services.routing import apply_route
from .widgets import RouteEditorWidget


class TourDayAdminForm(forms.ModelForm):
    class Meta:
        model = TourDay
        # `track` is computed by the route service, never typed in, so it is not a form field.
        fields = [
            "tour",
            "day_number",
            "title",
            "description",
            "distance_km",
            "ascent_m",
            "travel_time",
            "overnight",
            "track_source",
            "waypoints",
            "gpx_file",
        ]
        widgets = {"waypoints": RouteEditorWidget}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The map editor shows the saved line next to the points.
        self.fields["waypoints"].widget.track = self.instance.track

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        day = self.instance
        day.track_source = cleaned.get("track_source", day.track_source)
        day.waypoints = cleaned.get("waypoints") or []
        for field in ("distance_km", "ascent_m"):
            setattr(day, field, cleaned.get(field))
        gpx = cleaned.get("gpx_file")  # False when the client ticked «clear»
        try:
            apply_route(day, gpx_file=gpx or None)
        except RoutingError as exc:
            self.add_error("track_source", str(exc))
            return cleaned
        # Values computed by the route service go back into the form so they get saved.
        cleaned["waypoints"] = day.waypoints
        cleaned["distance_km"] = day.distance_km
        cleaned["ascent_m"] = day.ascent_m
        return cleaned
