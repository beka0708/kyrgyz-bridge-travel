from pathlib import Path
from urllib.parse import quote

from django.core.cache import cache
from django.core.validators import RegexValidator
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("создано", auto_now_add=True)
    updated_at = models.DateTimeField("изменено", auto_now=True)

    class Meta:
        abstract = True


class OrderableModel(models.Model):
    """Manual order; the admin lets the client drag rows to change it."""

    order = models.PositiveIntegerField("порядок", default=0, db_index=True)

    class Meta:
        abstract = True
        ordering = ["order", "pk"]


class PublishableQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)


class PublishableModel(models.Model):
    is_published = models.BooleanField("показывать на сайте", default=True)

    objects = PublishableQuerySet.as_manager()

    class Meta:
        abstract = True


class SEOModel(models.Model):
    seo_title = models.CharField(
        "SEO title",
        max_length=70,
        blank=True,
        help_text="Заголовок в Google, до 60 символов, на английском. Пусто — соберётся сам.",
    )
    seo_description = models.CharField(
        "SEO description",
        max_length=170,
        blank=True,
        help_text="Текст под заголовком в Google, 120–160 символов: что, где, для кого, цена. "
        "Пусто — краткое описание.",
    )
    og_image = models.ImageField(
        "картинка для превью в соцсетях",
        upload_to="seo/",
        blank=True,
        help_text="1200×630. Пусто — главное фото.",
    )

    class Meta:
        abstract = True


def default_privacy_policy():
    return (Path(__file__).parent / "legal" / "privacy_default.md").read_text(encoding="utf-8")


def default_terms():
    return (Path(__file__).parent / "legal" / "terms_default.md").read_text(encoding="utf-8")


LEGAL_HELP = (
    "На английском. «## Заголовок» — раздел, «- » — пункт, **текст** — жирный. "
    "Сами подставляются: {company} — название и реквизиты, {brand}, {email}, {site}, {updated}. "
    "Их заполняют поля выше; текст можно не трогать."
)


class Map3DMode(models.TextChoices):
    OFF = "off", "Выключен"
    DESKTOP = "desktop", "Только компьютеры"
    ALL = "all", "Везде, включая телефоны"


class SiteSettings(SEOModel):
    """Singleton with contacts and defaults; always use SiteSettings.load()."""

    CACHE_KEY = "site_settings"

    brand_name = models.CharField("название компании", max_length=100, default="Kyrgyz Tours")
    tagline = models.CharField("слоган", max_length=200, blank=True)
    phone = models.CharField("телефон", max_length=30, blank=True)
    whatsapp = models.CharField(
        "WhatsApp", max_length=20, blank=True, help_text="Только цифры с кодом страны: 996555123456"
    )
    telegram = models.CharField("Telegram", max_length=64, blank=True, help_text="Без @")
    email = models.EmailField("публичная почта", blank=True)
    inquiry_email = models.EmailField(
        "почта для заявок", blank=True, help_text="Сюда приходят письма о новых заявках."
    )
    address = models.CharField("адрес", max_length=255, blank=True)
    instagram_url = models.URLField("Instagram", blank=True)
    tiktok_url = models.URLField("TikTok", blank=True)
    facebook_url = models.URLField("Facebook", blank=True)
    youtube_url = models.URLField("YouTube", blank=True)
    tripadvisor_url = models.URLField("TripAdvisor", blank=True)
    map_3d_mode = models.CharField(
        "3D-рельеф на карте маршрута",
        max_length=10,
        choices=Map3DMode,
        default=Map3DMode.ALL,
        help_text="Наклон и объёмные горы. Тени рельефа видны всегда. Если на телефонах карта "
        "тормозит — выберите «Только компьютеры».",
    )
    # --- Home page texts (English); *stars* mark the accent part of a heading ---
    hero_title = models.CharField(
        "заголовок первого экрана",
        max_length=120,
        default="Mountains, lakes *and yurts*",
        help_text="Часть в *звёздочках* выделяется оранжевым.",
    )
    hero_subtitle = models.CharField(
        "подзаголовок первого экрана",
        max_length=200,
        default="Private and group tours across Kyrgyzstan with local guides.",
    )
    hero_image = models.ImageField(
        "фото первого экрана", upload_to="home/", blank=True, help_text="Широкое фото, от 2000 px."
    )
    solo_text = models.CharField(
        "текст «Private tours»",
        max_length=200,
        default=(
            "Your own route, your own pace and a personal guide. "
            "For couples and small groups of friends."
        ),
    )
    solo_image = models.ImageField("фото «Private tours»", upload_to="home/", blank=True)
    group_text = models.CharField(
        "текст «Group tours»",
        max_length=200,
        default="A small group, fixed dates and a better price.",
    )
    group_image = models.ImageField("фото «Group tours»", upload_to="home/", blank=True)
    about_title = models.CharField(
        "заголовок «О нас»", max_length=120, default="A team that *knows the mountains*"
    )
    about_eyebrow = models.CharField(
        "надпись над заголовком «О нас»",
        max_length=60,
        blank=True,
        default="The team",
        help_text="Мелкая строка над заголовком. Перед ней сам встанет «Since <год основания>».",
    )
    about_text = models.TextField("текст «О нас»", blank=True)
    about_link_label = models.CharField(
        "текст ссылки под «О нас»",
        max_length=40,
        blank=True,
        default="Meet the guides",
        help_text="Ведёт к блоку гидов. Пусто — ссылки нет.",
    )
    about_image = models.ImageField(
        "фото «О нас»",
        upload_to="home/",
        blank=True,
        help_text="Запасное: пока не загружены «Фото блока «О нас»», галерея собирается из "
        "этого фото, гидов и туров.",
    )

    trust_line = models.CharField(
        "строка доверия под кнопками",
        max_length=160,
        blank=True,
        default="Reply within 24 hours · No prepayment to ask · Local guides",
        help_text="Коротко и только правда: рейтинг, срок ответа, «без предоплаты». "
        "Разделитель « · ».",
    )
    rating_value = models.DecimalField(
        "рейтинг",
        max_digits=2,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Только настоящий, например 4.9 с Google. Пусто — блок рейтинга не показывается.",
    )
    rating_count = models.PositiveIntegerField("число отзывов", null=True, blank=True)
    rating_url = models.URLField(
        "ссылка на отзывы", blank=True, help_text="Страница с отзывами в Google или TripAdvisor"
    )
    reply_time = models.CharField(
        "срок ответа", max_length=40, default="within 24 hours", help_text="within 24 hours"
    )
    steps_image = models.ImageField("фото у блока «шаги»", upload_to="home/", blank=True)
    faq_image = models.ImageField("фото у блока FAQ", upload_to="home/", blank=True)
    request_image = models.ImageField("фото рядом с формой", upload_to="home/", blank=True)
    footer_image = models.ImageField("панорама над подвалом", upload_to="home/", blank=True)
    founder_name = models.CharField("имя основателя", max_length=100, blank=True)
    founder_role = models.CharField(
        "роль", max_length=100, blank=True, default="Founder & lead guide"
    )
    founder_photo = models.ImageField("фото основателя", upload_to="home/", blank=True)
    founder_quote = models.CharField(
        "цитата", max_length=200, blank=True, help_text="Одна фраза крупно, на английском."
    )
    founder_story = models.TextField(
        "история", blank=True, help_text="2–3 коротких абзаца на английском. Пусто — блок скрыт."
    )
    founder_since = models.PositiveSmallIntegerField(
        "год основания", null=True, blank=True, help_text="Например 2014"
    )
    founder_instagram = models.URLField(
        "Instagram основателя",
        blank=True,
        help_text="Ссылка на личный профиль: https://instagram.com/… Пусто — иконки нет.",
    )

    legal_name = models.CharField(
        "юр. название компании",
        max_length=150,
        blank=True,
        help_text="Например: Kyrgyz Bridge Travel LLC",
    )
    registration_number = models.CharField("регистрационный номер / ИНН", max_length=60, blank=True)
    legal_address = models.CharField("юридический адрес", max_length=200, blank=True)
    legal_email = models.EmailField(
        "email по вопросам данных",
        blank=True,
        help_text="Куда писать по поводу персональных данных. Пусто — публичная почта.",
    )
    legal_updated = models.DateField(
        "дата редакции документов", null=True, blank=True, help_text="Показывается вверху страниц."
    )
    privacy_policy = models.TextField(
        "политика конфиденциальности", default=default_privacy_policy, help_text=LEGAL_HELP
    )
    terms_of_use = models.TextField(
        "условия использования", default=default_terms, help_text=LEGAL_HELP
    )
    google_site_verification = models.CharField(
        "Google Search Console",
        max_length=100,
        blank=True,
        help_text="Код из мета-тега google-site-verification (только значение content). "
        "Не нужен, если домен подтверждён через DNS.",
    )
    bing_site_verification = models.CharField(
        "Bing Webmaster Tools",
        max_length=100,
        blank=True,
        help_text="Код из мета-тега msvalidate.01 (только значение content).",
    )
    google_analytics_id = models.CharField(
        "Google Analytics ID",
        max_length=32,
        blank=True,
        validators=[
            RegexValidator(
                r"^G-[A-Z0-9]{6,20}$", "Нужен ID вида G-ABC123XYZ9 (GA4 → Admin → Data streams)."
            )
        ],
        help_text="G-XXXXXXXXXX: Google Analytics → Admin → Data streams → сайт → "
        "Measurement ID. Пусто — аналитика выключена.",
    )

    class Meta:
        verbose_name = "настройки сайта"
        verbose_name_plural = "настройки сайта"

    def __str__(self):
        return "Настройки сайта"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(self.CACHE_KEY)

    def delete(self, *args, **kwargs):
        pass  # the singleton must always exist

    @classmethod
    def load(cls):
        obj = cache.get(cls.CACHE_KEY)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1)
            cache.set(cls.CACHE_KEY, obj, 60 * 10)
        return obj

    @property
    def telegram_url(self):
        return f"https://t.me/{self.telegram}" if self.telegram else ""

    def whatsapp_url(self, text=""):
        if not self.whatsapp:
            return ""
        url = f"https://wa.me/{self.whatsapp}"
        return f"{url}?text={quote(text)}" if text else url


def fill_legal(text: str, site: "SiteSettings") -> str:
    """Put the company details from the admin into a legal text ({company}, {email}, …).

    Only these placeholders are replaced, so any other braces in the text stay as written.
    """
    from django.conf import settings
    from django.utils.dateformat import format as date_format

    company = ", ".join(
        part
        for part in [
            site.legal_name or site.brand_name,
            f"registration no. {site.registration_number}" if site.registration_number else "",
            site.legal_address or site.address,
        ]
        if part
    )
    values = {
        "company": company,
        "brand": site.brand_name,
        "email": site.legal_email or site.email or site.inquiry_email or "the email in the footer",
        "site": settings.SITE_URL.split("://")[-1],
        "updated": date_format(site.legal_updated, "j F Y") if site.legal_updated else "—",
    }
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    return text
