import datetime

from django import forms

from apps.tours.models import Tour

from .models import REVIEW_HIGHLIGHTS, Review


class ReviewSubmitForm(forms.ModelForm):
    """«Share your experience» on the site. Saved hidden until the agency publishes it."""

    tour = forms.ModelChoiceField(
        queryset=Tour.objects.published(), to_field_name="slug", required=False
    )
    # <input type="month"> sends «2026-08»
    travel_month = forms.CharField(required=False, max_length=7)
    rating = forms.TypedChoiceField(
        choices=[(i, i) for i in range(1, 6)],
        coerce=int,
        error_messages={"required": "Please choose a rating from 1 to 5 stars."},
    )
    highlights = forms.MultipleChoiceField(choices=REVIEW_HIGHLIGHTS, required=False)
    website = forms.CharField(required=False)  # honeypot, hidden from people

    class Meta:
        model = Review
        fields = ["author_name", "country", "tour", "rating", "text", "email"]  # + highlights
        error_messages = {
            "author_name": {"required": "Please tell us your name."},
            "text": {"required": "Please write a few words about your trip."},
        }

    def clean_text(self):
        text = self.cleaned_data["text"].strip()
        if len(text) < 20:
            raise forms.ValidationError("A couple of sentences, please: at least 20 characters.")
        if len(text) > 3000:
            raise forms.ValidationError("That's a lot! Please keep it under 3,000 characters.")
        return text

    def clean_travel_month(self):
        value = self.cleaned_data.get("travel_month", "")
        if not value:
            return None
        try:
            year, month = (int(part) for part in value.split("-"))
            return datetime.date(year, month, 1)
        except (TypeError, ValueError):
            raise forms.ValidationError("Please pick the month of your trip.") from None

    def save(self, commit=True):
        review = super().save(commit=False)
        review.travel_date = self.cleaned_data.get("travel_month")
        review.highlights = ",".join(self.cleaned_data.get("highlights") or [])
        review.source = "site"
        review.is_published = False  # the agency reads it first
        review.order = 0
        if commit:
            review.save()
        return review
