import calendar

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count, Q
from django.urls import reverse

from apps.core.models import (
    OrderableModel,
    PublishableModel,
    PublishableQuerySet,
    SEOModel,
    TimeStampedModel,
)

MONTH_CHOICES = [(i, calendar.month_name[i]) for i in range(1, 13)]


class TourType(models.TextChoices):
    SOLO = "solo", "Одиночный"
    GROUP = "group", "Групповой"


# Labels on the public (English) site; the admin keeps the Russian choice labels.
PUBLIC_TOUR_TYPE = {TourType.SOLO: "Private tour", TourType.GROUP: "Group tour"}


class Difficulty(models.TextChoices):
    EASY = "easy", "Лёгкий"
    MODERATE = "moderate", "Средний"
    HARD = "hard", "Сложный"


PUBLIC_DIFFICULTY = {
    Difficulty.EASY: "Easy",
    Difficulty.MODERATE: "Moderate",
    Difficulty.HARD: "Challenging",
}


class Currency(models.TextChoices):
    USD = "USD", "USD"
    EUR = "EUR", "EUR"
    KGS = "KGS", "KGS"


class TourQuerySet(PublishableQuerySet):
    def for_cards(self):
        """Published tours with what a card shows: guest rating and the gallery (hover photo)."""
        published_reviews = Q(reviews__is_published=True)
        return (
            self.published()
            .annotate(
                rating_avg=Avg("reviews__rating", filter=published_reviews),
                rating_count=Count("reviews", filter=published_reviews),
            )
            .prefetch_related("images")
        )


class Tour(TimeStampedModel, OrderableModel, PublishableModel, SEOModel):
    title = models.CharField("название", max_length=150)
    slug = models.SlugField("адрес страницы", max_length=160, unique=True)
    tour_type = models.CharField("тип", max_length=10, choices=TourType.choices)
    short_description = models.CharField(
        "кратко", max_length=300, help_text="Для карточки тура и превью."
    )
    description = models.TextField("описание", blank=True)
    how_to_get_there = models.TextField("как добраться", blank=True)

    price_from = models.DecimalField(
        "цена от", max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    currency = models.CharField("валюта", max_length=3, choices=Currency, default=Currency.USD)
    price_note = models.CharField(
        "пояснение к цене", max_length=100, blank=True, help_text="Например: per person"
    )
    duration_days = models.PositiveSmallIntegerField(
        "длительность, дней", validators=[MinValueValidator(1)]
    )
    difficulty = models.CharField("сложность", max_length=10, choices=Difficulty.choices)
    max_altitude_m = models.PositiveIntegerField(
        "макс. высота, м",
        null=True,
        blank=True,
        help_text="Самая высокая точка маршрута, например 3920. Показывается на карточке тура.",
    )
    group_size_min = models.PositiveSmallIntegerField("группа от", default=1)
    group_size_max = models.PositiveSmallIntegerField("группа до", null=True, blank=True)
    season_start = models.PositiveSmallIntegerField(
        "сезон с", choices=MONTH_CHOICES, null=True, blank=True
    )
    season_end = models.PositiveSmallIntegerField(
        "сезон по", choices=MONTH_CHOICES, null=True, blank=True
    )

    cover = models.ImageField("главное фото", upload_to="tours/covers/")
    next_departure = models.CharField(
        "ближайший выезд",
        max_length=60,
        blank=True,
        help_text="Показывается на фото тура, например: June 14. Пусто — не показывать.",
    )
    is_featured = models.BooleanField("хит сезона", default=False)

    objects = TourQuerySet.as_manager()

    class Meta(OrderableModel.Meta):
        verbose_name = "тур"
        verbose_name_plural = "туры"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("tours:detail", kwargs={"slug": self.slug})

    def clean(self):
        if self.group_size_max and self.group_size_max < self.group_size_min:
            raise ValidationError({"group_size_max": "Не может быть меньше «группа от»."})
        if bool(self.season_start) != bool(self.season_end):
            raise ValidationError("Укажите оба месяца сезона или ни одного.")

    @property
    def type_label(self):
        return PUBLIC_TOUR_TYPE.get(self.tour_type, "")

    @property
    def difficulty_label(self):
        return PUBLIC_DIFFICULTY.get(self.difficulty, "")

    @property
    def group_label(self):
        if self.group_size_max:
            return f"up to {self.group_size_max} people"
        return f"from {self.group_size_min} people" if self.group_size_min > 1 else ""

    @property
    def price_label(self):
        symbols = {Currency.USD: "$", Currency.EUR: "€"}
        amount = f"{self.price_from:,.0f}"
        symbol = symbols.get(self.currency)
        return f"{symbol}{amount}" if symbol else f"{amount} {self.currency}"

    @property
    def price_display(self):
        """«from $390», or «Price on request» when the price is 0."""
        return f"from {self.price_label}" if self.price_from else "Price on request"

    @property
    def duration_label(self):
        days = self.duration_days
        return f"{days}\u00a0day{'' if days == 1 else 's'}"  # nbsp: never «4 / days»

    @property
    def altitude_label(self):
        return f"↑\u00a0{self.max_altitude_m:,}\u00a0m" if self.max_altitude_m else ""

    @property
    def difficulty_level(self):
        """1–3 for the difficulty meter on cards."""
        return {Difficulty.EASY: 1, Difficulty.MODERATE: 2, Difficulty.HARD: 3}.get(
            self.difficulty, 0
        )

    @property
    def hover_photo(self):
        """First gallery photo, shown on card hover (use with prefetch_related("images"))."""
        images = list(self.images.all())
        return images[0].image if images else None

    @property
    def is_winter(self):
        """Season starts in Nov–Feb: shown under the «Winter» filter."""
        return bool(self.season_start) and (self.season_start >= 11 or self.season_start <= 2)

    @property
    def filter_tags(self):
        """Space-separated tags for the home filter chips."""
        tags = [self.tour_type]
        if self.duration_days <= 2:
            tags.append("short")
        if self.is_winter:
            tags.append("winter")
        return " ".join(tags)

    @property
    def season_label(self):
        if not self.season_start:
            return ""
        start = calendar.month_abbr[self.season_start]
        end = calendar.month_abbr[self.season_end]
        return start if start == end else f"{start} – {end}"


class TourImage(OrderableModel):
    tour = models.ForeignKey(
        Tour, verbose_name="тур", on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField("фото", upload_to="tours/gallery/")
    alt = models.CharField("описание фото (alt)", max_length=200, blank=True)

    class Meta(OrderableModel.Meta):
        verbose_name = "фото галереи"
        verbose_name_plural = "галерея"

    def __str__(self):
        return self.alt or f"Фото {self.pk}"


class ListKind(models.TextChoices):
    INCLUDED = "included", "Включено"
    EXCLUDED = "excluded", "Не включено"
    GEAR = "gear", "Снаряжение"


class TourListItem(OrderableModel):
    tour = models.ForeignKey(
        Tour, verbose_name="тур", on_delete=models.CASCADE, related_name="list_items"
    )
    kind = models.CharField("раздел", max_length=10, choices=ListKind.choices)
    text = models.CharField("пункт", max_length=255)

    class Meta(OrderableModel.Meta):
        verbose_name = "пункт списка"
        verbose_name_plural = "включено / не включено / снаряжение"

    def __str__(self):
        return self.text


class TrackSource(models.TextChoices):
    MANUAL = "manual", "Прямые линии между точками"
    ROAD = "road", "По дорогам (машина)"
    HIKING = "hiking", "По пешим тропам"
    GPX = "gpx", "Из GPX-трека"


def validate_waypoints(value):
    """[{"lat": 42.49, "lng": 78.39, "name": "Karakol"}, ...]"""
    if not isinstance(value, list):
        raise ValidationError("Точки маршрута должны быть списком.")
    for i, point in enumerate(value, start=1):
        if not isinstance(point, dict):
            raise ValidationError(f"Точка {i}: ожидается объект.")
        try:
            lat, lng = float(point["lat"]), float(point["lng"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError(f"Точка {i}: нужны числа lat и lng.") from exc
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise ValidationError(f"Точка {i}: координаты вне диапазона.")


def validate_line_string(value):
    """GeoJSON LineString: {"type": "LineString", "coordinates": [[lng, lat], ...]}"""
    if value in (None, {}):
        return
    if not isinstance(value, dict) or value.get("type") != "LineString":
        raise ValidationError("Линия маршрута должна быть GeoJSON LineString.")
    coords = value.get("coordinates")
    if not isinstance(coords, list) or len(coords) < 2:
        raise ValidationError("В линии маршрута нужно минимум две точки.")


class TourDay(models.Model):
    tour = models.ForeignKey(
        Tour, verbose_name="тур", on_delete=models.CASCADE, related_name="days"
    )
    day_number = models.PositiveSmallIntegerField("день №", validators=[MinValueValidator(1)])
    title = models.CharField("заголовок", max_length=150, help_text="Например: Bishkek — Karakol")
    description = models.TextField("описание дня", blank=True)
    distance_km = models.DecimalField(
        "расстояние, км", max_digits=6, decimal_places=1, null=True, blank=True
    )
    ascent_m = models.PositiveIntegerField("набор высоты, м", null=True, blank=True)
    travel_time = models.CharField("время в пути", max_length=50, blank=True, help_text="5–6 h")
    overnight = models.CharField("ночёвка", max_length=150, blank=True)

    # Route geometry. Points are placed on a map in the admin; the line is computed once on
    # save (routing service, straight segments or GPX) so visitors never trigger a paid API.
    waypoints = models.JSONField(
        "точки маршрута", default=list, blank=True, validators=[validate_waypoints]
    )
    track = models.JSONField(
        "линия маршрута", null=True, blank=True, validators=[validate_line_string]
    )
    track_source = models.CharField(
        "как строить линию", max_length=10, choices=TrackSource, default=TrackSource.MANUAL
    )
    # Fingerprint of the inputs the current track was built from; the line is rebuilt only
    # when points, mode or GPX change, so saving a day does not spend routing quota.
    track_key = models.CharField(max_length=64, blank=True, editable=False)
    gpx_file = models.FileField(
        "GPX-трек",
        upload_to="tours/gpx/",
        blank=True,
        validators=[FileExtensionValidator(["gpx"])],
    )

    class Meta:
        verbose_name = "день маршрута"
        verbose_name_plural = "дни маршрута"
        ordering = ["tour", "day_number"]
        constraints = [
            models.UniqueConstraint(fields=["tour", "day_number"], name="unique_day_per_tour"),
        ]

    def __str__(self):
        return f"{self.tour} · день {self.day_number}: {self.title}"

    @property
    def meta_label(self):
        """«12 km · ↑ 900 m · 5–6 h · overnight: guesthouse» for the day card."""
        parts = []
        if self.distance_km is not None:
            parts.append(f"{self.distance_km:g}\u00a0km")
        if self.ascent_m:
            parts.append(f"↑\u00a0{self.ascent_m:,}\u00a0m")
        if self.travel_time:
            parts.append(self.travel_time)
        if self.overnight:
            parts.append(f"overnight: {self.overnight}")
        return " · ".join(parts)


class TourDayImage(OrderableModel):
    day = models.ForeignKey(
        TourDay, verbose_name="день", on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField("фото", upload_to="tours/days/")
    alt = models.CharField("описание фото (alt)", max_length=200, blank=True)

    class Meta(OrderableModel.Meta):
        verbose_name = "фото дня"
        verbose_name_plural = "фото дня"

    def __str__(self):
        return self.alt or f"Фото {self.pk}"
