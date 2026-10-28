from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.models import SiteSettings
from apps.tours.models import ListKind, Tour, TourDay


class ImageSerializer(serializers.Serializer):
    url = serializers.SerializerMethodField()
    alt = serializers.CharField()

    def get_url(self, obj) -> str:
        request = self.context.get("request")
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


class TourListSerializer(serializers.ModelSerializer):
    cover = serializers.ImageField(read_only=True)
    season = serializers.CharField(source="season_label", read_only=True)
    url = serializers.CharField(source="get_absolute_url", read_only=True)

    class Meta:
        model = Tour
        fields = [
            "id",
            "slug",
            "url",
            "title",
            "tour_type",
            "short_description",
            "price_from",
            "currency",
            "price_note",
            "duration_days",
            "difficulty",
            "group_size_min",
            "group_size_max",
            "season",
            "cover",
            "is_featured",
        ]


class TourDaySerializer(serializers.ModelSerializer):
    images = ImageSerializer(many=True, read_only=True)

    class Meta:
        model = TourDay
        fields = [
            "day_number",
            "title",
            "description",
            "distance_km",
            "ascent_m",
            "travel_time",
            "overnight",
            "images",
        ]


class SEOSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField()
    image = serializers.CharField(allow_null=True)


class TourDetailSerializer(TourListSerializer):
    days = TourDaySerializer(many=True, read_only=True)
    images = ImageSerializer(many=True, read_only=True)
    included = serializers.SerializerMethodField()
    excluded = serializers.SerializerMethodField()
    gear = serializers.SerializerMethodField()
    whatsapp_url = serializers.SerializerMethodField()
    seo = serializers.SerializerMethodField()

    class Meta(TourListSerializer.Meta):
        fields = [
            *TourListSerializer.Meta.fields,
            "description",
            "how_to_get_there",
            "included",
            "excluded",
            "gear",
            "days",
            "images",
            "whatsapp_url",
            "seo",
        ]

    def _list(self, obj, kind):
        # list_items are prefetched; filter in Python to avoid extra queries
        return [item.text for item in obj.list_items.all() if item.kind == kind]

    def get_included(self, obj) -> list[str]:
        return self._list(obj, ListKind.INCLUDED)

    def get_excluded(self, obj) -> list[str]:
        return self._list(obj, ListKind.EXCLUDED)

    def get_gear(self, obj) -> list[str]:
        return self._list(obj, ListKind.GEAR)

    def get_whatsapp_url(self, obj) -> str:
        return SiteSettings.load().whatsapp_url(f"Hi! I'm interested in the tour «{obj.title}».")

    @extend_schema_field(SEOSerializer)
    def get_seo(self, obj):
        request = self.context.get("request")
        image = obj.og_image or obj.cover
        image_url = image.url if image else None
        if image_url and request:
            image_url = request.build_absolute_uri(image_url)
        return {
            "title": obj.seo_title or obj.title,
            "description": obj.seo_description or obj.short_description,
            "image": image_url,
        }


class RouteDaySerializer(serializers.ModelSerializer):
    waypoints = serializers.JSONField()
    track = serializers.JSONField(allow_null=True)

    class Meta:
        model = TourDay
        fields = ["day_number", "title", "waypoints", "track"]


class TourRouteSerializer(serializers.Serializer):
    """Everything the map island needs: per-day points and lines plus overall bounds."""

    slug = serializers.SlugField()
    days = RouteDaySerializer(many=True)
    bounds = serializers.ListField(
        child=serializers.FloatField(),
        allow_null=True,
        help_text="[west, south, east, north] over all points and lines",
    )
