from django import forms
from unfold.widgets import (
    UnfoldAdminIntegerFieldWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminTextInputWidget,
)

from .models import Tour, TourDay
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


class NativeDateWidget(UnfoldAdminTextInputWidget):
    """The browser's own date picker (a calendar on click, on phones too), in unfold's style."""

    input_type = "date"

    def format_value(self, value):
        return value.isoformat() if hasattr(value, "isoformat") else value


EVERY_CHOICES = [
    (7, "Каждую неделю (в тот же день недели)"),
    (10, "Каждые 10 дней"),
    (14, "Раз в 2 недели"),
    (21, "Раз в 3 недели"),
    (28, "Раз в 4 недели"),
    (0, "Только эту дату"),
]


class DeparturePlanForm(forms.Form):
    """«Запланировать выезды»: a first date and how often; the dates are shown before saving."""

    tour = forms.ModelChoiceField(
        label="Тур", queryset=Tour.objects.all(), widget=UnfoldAdminSelectWidget
    )
    first_date = forms.DateField(label="Первый выезд", widget=NativeDateWidget())
    every_days = forms.TypedChoiceField(
        label="Как часто",
        choices=EVERY_CHOICES,
        coerce=int,
        initial=7,
        widget=UnfoldAdminSelectWidget,
    )
    until = forms.DateField(
        label="До какой даты",
        required=False,
        widget=NativeDateWidget(),
        help_text="Пусто — на год вперёд. Даты вне сезона тура пропускаются сами.",
    )
    seats_left = forms.IntegerField(
        label="Мест в группе",
        required=False,
        min_value=0,
        widget=UnfoldAdminIntegerFieldWidget,
        help_text="Пусто — возьмём «группа до» из тура.",
    )

    def clean(self):
        from datetime import timedelta

        from django.utils import timezone

        from .services.departures import repeat_dates

        cleaned = super().clean()
        tour, first = cleaned.get("tour"), cleaned.get("first_date")
        if not tour or not first:
            return cleaned
        every = cleaned.get("every_days") or 0
        if every:
            until = cleaned.get("until") or first + timedelta(days=365)
            days = repeat_dates(first, every, until, (tour.season_start, tour.season_end))
        else:
            days = [first]
        days = [d for d in days if d >= timezone.localdate()]
        if not days:
            raise forms.ValidationError(
                "Не получилось ни одной будущей даты в сезон тура — проверьте даты и сезон."
            )
        if len(days) > 120:
            raise forms.ValidationError(f"Получилось {len(days)} дат — проверьте «до какой даты».")
        cleaned["days"] = days
        if cleaned.get("seats_left") is None:
            cleaned["seats_left"] = tour.group_size_max
        return cleaned
