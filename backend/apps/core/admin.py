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
# Tours: the same fields plus «how Google shows it» (readonly `google_preview`)
SEO_PREVIEW_FIELDSET = (
    "SEO",
    {
        "classes": ["tab"],
        "description": "Заполнять не обязательно: пусто — сайт сам соберёт заголовок и описание "
        "из названия и краткого текста. Свои — если хотите вставить ключевые слова, "
        "по которым ищут туристы (например «Kyrgyzstan horse riding tour»).",
        "fields": ["google_preview", "seo_title", "seo_description", "og_image"],
    },
)


def google_preview(meta):
    """A search result as Google shows it, with length hints (title ≤ 60, description ≤ 160)."""
    if meta is None:
        return "Сохраните, чтобы увидеть предпросмотр."
    title_len, desc_len = len(meta.title), len(meta.description)

    def hint(n, limit):
        color = "#2fa564" if n <= limit else "#dc2626"
        note = "хорошо" if n <= limit else "длинно — Google обрежет"
        return format_html('<span style="color:{}">{} символов — {}</span>', color, n, note)

    return format_html(
        '<div style="max-width:620px;padding:14px 16px;border:1px solid rgb(0 0 0/.1);'
        'border-radius:12px;font-family:arial,sans-serif;background:#fff;color:#202124">'
        '<div style="font-size:13px;color:#4d5156">{url}</div>'
        '<div style="font-size:19px;color:#1a0dab;line-height:1.3;margin:4px 0">{title}</div>'
        '<div style="font-size:14px;color:#4d5156;line-height:1.5">{desc}</div></div>'
        '<div style="font-size:12px;margin-top:6px">Заголовок: {th} · Описание: {dh}</div>',
        url=meta.canonical,
        title=meta.title[:70] + ("…" if title_len > 70 else ""),
        desc=meta.description,
        th=hint(title_len, 60),
        dh=hint(desc_len, 160),
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
                    "about_eyebrow",
                    "about_title",
                    "about_text",
                    "about_link_label",
                    "about_image",
                    ("founder_name", "founder_role", "founder_since"),
                    ("founder_photo", "founder_instagram"),
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
                "description": "Иконки в подвале сайта. Пустое поле — иконки нет.",
                "fields": [
                    "instagram_url",
                    "tiktok_url",
                    "facebook_url",
                    "tripadvisor_url",
                    "youtube_url",
                ],
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
