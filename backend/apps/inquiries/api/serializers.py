from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.inquiries.contact import normalize_contact
from apps.inquiries.models import Inquiry
from apps.tours.models import Departure, Tour


class InquiryCreateSerializer(serializers.ModelSerializer):
    tour = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Tour.objects.published(),
        required=False,
        allow_null=True,
        help_text="Tour slug; empty for a general question.",
    )
    departure = serializers.PrimaryKeyRelatedField(
        queryset=Departure.objects.upcoming(),
        required=False,
        allow_null=True,
        help_text="A date picked in the tour calendar.",
    )
    # Honeypot: hidden in the form, real people leave it empty.
    website = serializers.CharField(
        write_only=True, required=False, allow_blank=True, help_text="Leave empty (anti-spam)."
    )
    turnstile_token = serializers.CharField(write_only=True, required=False, allow_blank=True)

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
            "website",
            "turnstile_token",
        ]

    def validate(self, attrs):
        try:
            attrs["email"], attrs["contact"] = normalize_contact(
                attrs.get("email", ""), attrs.get("contact", "")
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"contact": exc.messages[0]}) from None
        date_from, date_to = attrs.get("date_from"), attrs.get("date_to")
        if date_from and date_to and date_to < date_from:
            raise serializers.ValidationError({"date_to": "End date is before start date."})
        departure, tour = attrs.get("departure"), attrs.get("tour")
        if departure and tour and departure.tour_id != tour.pk:
            raise serializers.ValidationError({"departure": "This date belongs to another tour."})
        return attrs


class InquiryResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default="received")
