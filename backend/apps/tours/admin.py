from django.contrib import admin
from django.db.models import Count
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.decorators import display

from apps.core.admin import SEO_FIELDSET, thumbnail

from .models import Tour, TourDay, TourDayImage, TourImage, TourListItem, TourType


class TourDayInline(StackedInline):
    model = TourDay
    extra = 0
    tab = True
    show_change_link = True  # photos and the route map are edited on the day's own page
    fields = [
        ("day_number", "title"),
        "description",
        ("distance_km", "ascent_m", "travel_time"),
        "overnight",
    ]


class TourImageInline(TabularInline):
    model = TourImage
    extra = 0
    tab = True
    ordering_field = "order"
    hide_ordering_field = True
    fields = ["preview", "image", "alt", "order"]
    readonly_fields = ["preview"]

    @display(description="")
    def preview(self, obj):
        return thumbnail(obj.image)


class TourListItemInline(TabularInline):
    model = TourListItem
    extra = 0
    tab = True
    ordering_field = "order"
    hide_ordering_field = True
    fields = ["kind", "text", "order"]
    verbose_name_plural = "Включено / не включено / снаряжение"


@admin.register(Tour)
class TourAdmin(ModelAdmin):
    list_display = [
        "cover_preview",
        "title",
        "type_label",
        "price",
        "duration_days",
        "days_count",
        "is_featured",
        "is_published",
    ]
    list_display_links = ["cover_preview", "title"]
    list_editable = ["is_featured", "is_published"]
    list_filter = ["tour_type", "difficulty", "is_published", "is_featured"]
    search_fields = ["title", "short_description"]
    prepopulated_fields = {"slug": ["title"]}
    ordering_field = "order"
    hide_ordering_field = True
    save_on_top = True
    inlines = [TourDayInline, TourImageInline, TourListItemInline]
    fieldsets = [
        (
            "Основное",
            {
                "classes": ["tab"],
                "fields": [
                    "title",
                    "slug",
                    "tour_type",
                    "cover",
                    "short_description",
                    "description",
                    "how_to_get_there",
                    ("is_published", "is_featured"),
                ],
            },
        ),
        (
            "Цена и параметры",
            {
                "classes": ["tab"],
                "fields": [
                    ("price_from", "currency", "price_note"),
                    ("duration_days", "difficulty"),
                    ("group_size_min", "group_size_max"),
                    ("season_start", "season_end"),
                ],
            },
        ),
        SEO_FIELDSET,
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_days_count=Count("days"))

    @display(description="")
    def cover_preview(self, obj):
        return thumbnail(obj.cover)

    @display(
        description="тип",
        ordering="tour_type",
        label={TourType.SOLO: "info", TourType.GROUP: "success"},
    )
    def type_label(self, obj):
        return obj.tour_type, obj.get_tour_type_display()

    @display(description="цена от", ordering="price_from")
    def price(self, obj):
        return f"{obj.price_from:g} {obj.currency}"

    @display(description="дней в программе", ordering="_days_count")
    def days_count(self, obj):
        return obj._days_count


class TourDayImageInline(TabularInline):
    model = TourDayImage
    extra = 0
    ordering_field = "order"
    hide_ordering_field = True
    fields = ["preview", "image", "alt", "order"]
    readonly_fields = ["preview"]

    @display(description="")
    def preview(self, obj):
        return thumbnail(obj.image)


@admin.register(TourDay)
class TourDayAdmin(ModelAdmin):
    list_display = ["tour", "day_number", "title", "points_count", "has_track"]
    list_display_links = ["day_number", "title"]
    list_filter = ["tour"]
    list_select_related = ["tour"]
    search_fields = ["title", "tour__title"]
    autocomplete_fields = ["tour"]
    inlines = [TourDayImageInline]
    fieldsets = [
        (
            "День",
            {
                "fields": [
                    "tour",
                    ("day_number", "title"),
                    "description",
                    ("distance_km", "ascent_m", "travel_time"),
                    "overnight",
                ]
            },
        ),
        (
            "Маршрут на карте",
            {
                # Temporary raw JSON; replaced by the map editor (Vue island) in the next stage.
                "description": "Скоро здесь будет карта: точки ставятся кликом, линия строится "
                "автоматически. Пока — JSON.",
                "fields": ["track_source", "waypoints", "gpx_file", "track"],
            },
        ),
    ]

    @display(description="точек")
    def points_count(self, obj):
        return len(obj.waypoints or [])

    @display(description="линия", boolean=True)
    def has_track(self, obj):
        return bool(obj.track)
