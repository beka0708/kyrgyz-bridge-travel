from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import OrderableModel, PublishableModel, TimeStampedModel


class Guide(OrderableModel, PublishableModel):
    name = models.CharField("имя", max_length=100)
    role = models.CharField("роль", max_length=100, blank=True, help_text="Mountain guide")
    quote = models.CharField(
        "цитата", max_length=200, blank=True, help_text="Короткая фраза гида, на английском."
    )
    bio = models.TextField("о гиде", blank=True)
    photo = models.ImageField("фото", upload_to="guides/")
    languages = models.CharField("языки", max_length=100, blank=True, help_text="EN, RU, KG")
    experience_years = models.PositiveSmallIntegerField("опыт, лет", null=True, blank=True)

    class Meta(OrderableModel.Meta):
        verbose_name = "гид"
        verbose_name_plural = "гиды"

    def __str__(self):
        return self.name


class ReviewSource(models.TextChoices):
    DIRECT = "direct", "Напрямую"
    GOOGLE = "google", "Google"
    TRIPADVISOR = "tripadvisor", "TripAdvisor"
    INSTAGRAM = "instagram", "Instagram"
    SITE = "site", "Форма на сайте"


# Chips on the review form: what a guest liked (rating 4–5) or wants improved (rating 1–3).
REVIEW_HIGHLIGHTS = [
    ("guides", "Guides"),
    ("scenery", "Scenery"),
    ("food", "Food"),
    ("stays", "Yurts & stays"),
    ("organisation", "Organisation"),
    ("transport", "Transport"),
    ("value", "Value for money"),
    ("group", "Group"),
]
HIGHLIGHT_LABELS_RU = {
    "guides": "гиды",
    "scenery": "природа",
    "food": "еда",
    "stays": "юрты и ночёвки",
    "organisation": "организация",
    "transport": "транспорт",
    "value": "цена",
    "group": "группа",
}


class Review(TimeStampedModel, OrderableModel, PublishableModel):
    author_name = models.CharField("имя автора", max_length=100)
    country = models.CharField("страна", max_length=60, blank=True)
    rating = models.PositiveSmallIntegerField(
        "оценка", default=5, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    text = models.TextField("текст отзыва")
    photo = models.ImageField("фото автора", upload_to="reviews/", blank=True)
    tour = models.ForeignKey(
        "tours.Tour",
        verbose_name="тур",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
    )
    source = models.CharField(
        "источник", max_length=20, choices=ReviewSource.choices, default=ReviewSource.DIRECT
    )
    source_url = models.URLField("ссылка на оригинал", blank=True)
    travel_date = models.DateField("дата поездки", null=True, blank=True)
    highlights = models.CharField(
        "отметил(а)",
        max_length=200,
        blank=True,
        help_text="Что понравилось (оценка 4–5) или что улучшить (1–3) — чипы на форме отзыва.",
    )
    email = models.EmailField(
        "email автора",
        blank=True,
        help_text="Только для связи с автором, на сайте не показывается.",
    )

    class Meta(OrderableModel.Meta):
        verbose_name = "отзыв"
        verbose_name_plural = "отзывы"

    def __str__(self):
        return f"{self.author_name} ({self.rating}★)"

    @property
    def highlights_ru(self):
        return ", ".join(
            HIGHLIGHT_LABELS_RU.get(key, key) for key in self.highlights.split(",") if key
        )

    @property
    def public_source(self):
        """«Google», «TripAdvisor», «Instagram» for the site; nothing for direct or site reviews."""
        return {"google": "Google", "tripadvisor": "TripAdvisor", "instagram": "Instagram"}.get(
            self.source, ""
        )


class FAQ(OrderableModel, PublishableModel):
    question = models.CharField("вопрос", max_length=255)
    answer = models.TextField("ответ")

    class Meta(OrderableModel.Meta):
        verbose_name = "вопрос"
        verbose_name_plural = "частые вопросы"

    def __str__(self):
        return self.question


class Partner(OrderableModel, PublishableModel):
    name = models.CharField("название", max_length=100)
    logo = models.ImageField("логотип", upload_to="partners/")
    url = models.URLField("сайт", blank=True)

    class Meta(OrderableModel.Meta):
        verbose_name = "партнёр"
        verbose_name_plural = "партнёры"

    def __str__(self):
        return self.name


class GalleryPost(OrderableModel, PublishableModel):
    """«Живые кадры»: a manual Instagram-like feed, no Instagram API tokens to expire."""

    image = models.ImageField("фото", upload_to="gallery/")
    caption = models.CharField("подпись", max_length=200, blank=True)
    link = models.URLField("ссылка на пост", blank=True)

    class Meta(OrderableModel.Meta):
        verbose_name = "кадр"
        verbose_name_plural = "живые кадры"

    def __str__(self):
        return self.caption or f"Кадр {self.pk}"


class Stat(OrderableModel, PublishableModel):
    """Counters in the «About us» block: 12+ years, 3000 guests, …"""

    value = models.PositiveIntegerField("число")
    suffix = models.CharField("после числа", max_length=10, blank=True, help_text="+, %, k")
    label = models.CharField("подпись", max_length=60)

    class Meta(OrderableModel.Meta):
        verbose_name = "счётчик"
        verbose_name_plural = "счётчики"

    def __str__(self):
        return f"{self.value}{self.suffix} {self.label}"


class Feature(OrderableModel, PublishableModel):
    """«Why us» tiles on the home page: a photo with a short caption."""

    title = models.CharField("заголовок", max_length=80)
    text = models.CharField("текст", max_length=240)
    image = models.ImageField("фото", upload_to="features/", blank=True)

    class Meta(OrderableModel.Meta):
        verbose_name = "преимущество"
        verbose_name_plural = "почему мы"

    def __str__(self):
        return self.title


class Season(OrderableModel, PublishableModel):
    """«When to go» panels: what each season looks like in Kyrgyzstan."""

    months = models.CharField("месяцы", max_length=40, help_text="June – July")
    title = models.CharField("заголовок", max_length=80, help_text="Green pastures")
    text = models.CharField("текст", max_length=200)
    image = models.ImageField("фото", upload_to="seasons/")
    tour = models.ForeignKey(
        "tours.Tour",
        verbose_name="тур для ссылки",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Пусто — ссылка на список туров.",
    )

    class Meta(OrderableModel.Meta):
        verbose_name = "сезон"
        verbose_name_plural = "когда ехать (сезоны)"

    def __str__(self):
        return f"{self.months}: {self.title}"
