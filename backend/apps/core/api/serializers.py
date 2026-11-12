from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.maps import map_config
from apps.core.models import Map3DMode, SiteSettings


class MapTopoSerializer(serializers.Serializer):
    tiles = serializers.ListField(child=serializers.CharField())
    attribution = serializers.CharField()


class MapTerrainSerializer(serializers.Serializer):
    tiles = serializers.CharField()
    encoding = serializers.CharField()
    attribution = serializers.CharField()


class MapConfigSerializer(serializers.Serializer):
    style_url = serializers.CharField(help_text="MapLibre vector style (OpenFreeMap by default)")
    topo = MapTopoSerializer(help_text="Raster topo layer for the «Topo» switch")
    terrain = MapTerrainSerializer(help_text="Elevation tiles for hillshade and 3D")
    terrain_3d = serializers.ChoiceField(
        choices=Map3DMode.choices, help_text="Where 3D tilt is enabled; set in the admin"
    )


class SiteSettingsSerializer(serializers.ModelSerializer):
    whatsapp_url = serializers.SerializerMethodField()
    telegram_url = serializers.SerializerMethodField()
    map = serializers.SerializerMethodField()

    class Meta:
        model = SiteSettings
        fields = [
            "brand_name",
            "tagline",
            "phone",
            "whatsapp",
            "whatsapp_url",
            "telegram",
            "telegram_url",
            "email",
            "address",
            "instagram_url",
            "tiktok_url",
            "facebook_url",
            "youtube_url",
            "tripadvisor_url",
            "map",
        ]

    def get_whatsapp_url(self, obj) -> str:
        return obj.whatsapp_url()

    @extend_schema_field(MapConfigSerializer)
    def get_map(self, obj):
        return map_config()

    def get_telegram_url(self, obj) -> str:
        return f"https://t.me/{obj.telegram}" if obj.telegram else ""
