from urllib.parse import quote

from django.core.cache import cache
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
        "SEO title", max_length=70, blank=True, help_text="До 60–70 символов. Пусто — название."
    )
    seo_description = models.CharField(
        "SEO description", max_length=170, blank=True, help_text="До 150–160 символов."
    )
    og_image = models.ImageField(
        "картинка для превью в соцсетях",
        upload_to="seo/",
        blank=True,
        help_text="1200×630. Пусто — главное фото.",
    )

    class Meta:
        abstract = True


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
    about_text = models.TextField("текст «О нас»", blank=True)
    about_image = models.ImageField("фото «О нас»", upload_to="home/", blank=True)

    google_analytics_id = models.CharField(
        "Google Analytics ID", max_length=32, blank=True, help_text="G-XXXXXXXXXX"
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
