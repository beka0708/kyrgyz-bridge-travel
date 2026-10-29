from django import forms

from apps.tours.models import Tour

from .models import Inquiry


class InquiryForm(forms.ModelForm):
    """Same fields as the API serializer; used when the page is submitted without JavaScript."""

    tour = forms.ModelChoiceField(
        queryset=Tour.objects.published(), to_field_name="slug", required=False
    )
    website = forms.CharField(required=False)  # honeypot, hidden from people

    class Meta:
        model = Inquiry
        fields = [
            "name",
            "email",
            "contact",
            "tour",
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
        date_from, date_to = cleaned.get("date_from"), cleaned.get("date_to")
        if date_from and date_to and date_to < date_from:
            self.add_error("date_to", "End date is before start date.")
        return cleaned
