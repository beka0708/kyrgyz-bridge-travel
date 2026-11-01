from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.inquiries.contact import normalize_contact
from apps.inquiries.models import Inquiry
from apps.tours.models import Tour


class InquiryCreateSerializer(serializers.ModelSerializer):
    tour = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Tour.objects.published(),
        required=False,
        allow_null=True,
        help_text="Tour slug; empty for a general question.",
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
        return attrs


class InquiryResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default="received")
