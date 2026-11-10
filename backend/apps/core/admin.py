from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import SiteSettings


def thumbnail(image, size=48):
    """Small preview for list_display columns."""
    if not image:
        return "—"
    # min-width: unfold's list cells are min-w-0 and would squash the image to ~1px
    return format_html(
        '<img src="{url}" style="width:{s}px;min-width:{s}px;height:{s}px;'
        'object-fit:cover;border-radius:6px">',
        url=image.url,
        s=size,
    )


SEO_FIELDSET = (
    "SEO",
    {"classes": ["tab"], "fields": ["seo_title", "seo_description", "og_image"]},
)


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    fieldsets = [
        ("Компания", {"classes": ["tab"], "fields": ["brand_name", "tagline", "address"]}),
        (
            "Главная",
            {
                "classes": ["tab"],
                "fields": [
                    "hero_title",
                    "hero_subtitle",
                    "hero_image",
                    ("solo_text", "solo_image"),
                    ("group_text", "group_image"),
                    "about_title",
                    "about_text",
                    "about_image",
                    ("founder_name", "founder_role", "founder_since"),
                    "founder_photo",
                    "founder_quote",
                    "founder_story",
                    "trust_line",
                    ("rating_value", "rating_count", "rating_url"),
                    "reply_time",
                    ("steps_image", "faq_image"),
                    ("request_image", "footer_image"),
                ],
            },
        ),
        (
            "Контакты",
            {
                "classes": ["tab"],
                "fields": ["phone", "whatsapp", "email", "inquiry_email"],
            },
        ),
        (
            "Соцсети",
            {
                "classes": ["tab"],
                "fields": ["instagram_url", "facebook_url", "youtube_url", "tripadvisor_url"],
            },
        ),
        ("Карта", {"classes": ["tab"], "fields": ["map_3d_mode"]}),
        (
            "Правовое",
            {
                "classes": ["tab"],
                "description": "Заполните реквизиты — они сами подставятся в тексты политики и "
                "условий. Тексты — стандартные для туристических сайтов; менять не обязательно.",
                "fields": [
                    ("legal_name", "registration_number"),
                    ("legal_address", "legal_email"),
                    "legal_updated",
                    "privacy_policy",
                    "terms_of_use",
                ],
            },
        ),
        (
            "SEO и аналитика",
            {
                "classes": ["tab"],
                "fields": [
                    "seo_title",
                    "seo_description",
                    "og_image",
                    "google_analytics_id",
                    ("google_site_verification", "bing_site_verification"),
                ],
            },
        ),
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SiteSettings.load()
        return redirect(reverse("admin:core_sitesettings_change", args=[obj.pk]))


# Re-register auth models with unfold styling.
admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass
