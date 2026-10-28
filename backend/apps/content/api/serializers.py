from rest_framework import serializers

from apps.content.models import FAQ, GalleryPost, Guide, Partner, Review, Stat


class GuideSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guide
        fields = ["id", "name", "role", "quote", "bio", "photo", "languages", "experience_years"]


class ReviewSerializer(serializers.ModelSerializer):
    tour_slug = serializers.SlugRelatedField(source="tour", slug_field="slug", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "author_name",
            "country",
            "rating",
            "text",
            "photo",
            "tour_slug",
            "source",
            "source_url",
            "travel_date",
        ]


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ["id", "question", "answer"]


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = ["id", "name", "logo", "url"]


class GalleryPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = GalleryPost
        fields = ["id", "image", "caption", "link"]


class StatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stat
        fields = ["id", "value", "suffix", "label"]
