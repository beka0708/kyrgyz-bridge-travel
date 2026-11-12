from django import forms
from django.core.exceptions import ValidationError

from apps.tours.models import Departure, Tour

from .contact import normalize_contact
from .models import Inquiry


class InquiryForm(forms.ModelForm):
    """Same fields as the API serializer; used when the page is submitted without JavaScript."""

    tour = forms.ModelChoiceField(
        queryset=Tour.objects.published(), to_field_name="slug", required=False
    )
    departure = forms.ModelChoiceField(queryset=Departure.objects.upcoming(), required=False)
    website = forms.CharField(required=False)  # honeypot, hidden from people

    class Meta:
        model = Inquiry
        fields = [
            "name",
            "email",
            "contact",
            "tour",
            "departure",
            "travel_when",
            "date_from",
            "date_to",
            "people",
            "comment",
            "page_url",
            "utm_source",
            "utm_medium",
            "utm_campaign",
        ]

    def clean(self):
        cleaned = super().clean()
        try:
            cleaned["email"], cleaned["contact"] = normalize_contact(
                cleaned.get("email", ""), cleaned.get("contact", "")
            )
        except ValidationError as exc:
            self.add_error("contact", exc.messages[0])
        date_from, date_to = cleaned.get("date_from"), cleaned.get("date_to")
        if date_from and date_to and date_to < date_from:
            self.add_error("date_to", "End date is before start date.")
        departure, tour = cleaned.get("departure"), cleaned.get("tour")
        if departure and tour and departure.tour_id != tour.pk:
            self.add_error("departure", "This date belongs to another tour.")
        return cleaned
