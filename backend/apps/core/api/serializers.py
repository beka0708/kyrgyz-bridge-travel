from rest_framework import serializers

from apps.core.models import SiteSettings


class SiteSettingsSerializer(serializers.ModelSerializer):
    whatsapp_url = serializers.SerializerMethodField()
    telegram_url = serializers.SerializerMethodField()

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
            "facebook_url",
            "youtube_url",
            "tripadvisor_url",
        ]

    def get_whatsapp_url(self, obj) -> str:
        return obj.whatsapp_url()

    def get_telegram_url(self, obj) -> str:
        return f"https://t.me/{obj.telegram}" if obj.telegram else ""
