from datetime import timedelta

from django.contrib import admin, messages
from django.db.models import Count
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.decorators import action, display

from apps.core.admin import SEO_PREVIEW_FIELDSET, google_preview, thumbnail

from .forms import DeparturePlanForm, TourDayAdminForm
from .models import (
    Departure,
    DepartureStatus,
    Tour,
    TourDay,
    TourDayImage,
    TourImage,
    TourListItem,
    TourType,
)
from .services.departures import create_departures


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


class DepartureInline(TabularInline):
    """Upcoming dates of the tour; the whole season is planned in «Расписание выездов»."""

    model = Departure
    extra = 0
    tab = True
    fields = ["start_date", "end_date", "seats_left", "price", "note"]
    readonly_fields = ["end_date"]
    verbose_name_plural = "Даты выездов"

    def get_queryset(self, request):
        return super().get_queryset(request).filter(start_date__gte=timezone.localdate())


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
    inlines = [TourDayInline, DepartureInline, TourImageInline, TourListItemInline]
    fieldsets = [
        (
            "Основное",
            {
                "classes": ["tab"],
                "fields": [
                    "title",
                    "slug",
                    "tour_type",
                    "schedule",
                    ("cover", "next_departure"),
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
                    ("duration_days", "difficulty", "max_altitude_m"),
                    ("group_size_min", "group_size_max"),
                    ("season_start", "season_end"),
                ],
            },
        ),
        SEO_PREVIEW_FIELDSET,
    ]
    readonly_fields = ["google_preview", "schedule"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_days_count=Count("days"))

    @display(description="Расписание")
    def schedule(self, obj):
        from django.utils.html import format_html

        plan = reverse("admin:tours_departure_plan")
        if not obj.pk:
            return "Сохраните тур, затем добавьте даты выездов."
        count = obj.departures.filter(start_date__gte=timezone.localdate()).count()
        listing = reverse("admin:tours_departure_changelist") + f"?tour__id__exact={obj.pk}"
        return format_html(
            '<b>{}</b> предстоящих выездов · <a href="{}" class="text-primary-600 font-semibold">'
            'Открыть расписание</a> · <a href="{}?tour={}" class="text-primary-600 font-semibold">'
            "Запланировать даты</a>",
            count,
            listing,
            plan,
            obj.pk,
        )

    @display(description="Как увидит Google")
    def google_preview(self, obj):
        from apps.core.models import SiteSettings
        from apps.core.seo import tour_meta

        if not obj.pk:
            return google_preview(None)
        return google_preview(tour_meta(SiteSettings.load(), obj, list(obj.days.all())))

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
    form = TourDayAdminForm
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
                "description": "Расставьте точки на карте и выберите, как соединить их линией. "
                "Линия строится при сохранении (или сразу кнопкой «Построить линию»). "
                "Расстояние и набор высоты заполнятся сами, если поля пустые.",
                "fields": ["track_source", "waypoints", "gpx_file"],
            },
        ),
    ]

    @display(description="точек")
    def points_count(self, obj):
        return len(obj.waypoints or [])

    @display(description="линия", boolean=True)
    def has_track(self, obj):
        return bool(obj.track)


class WhenFilter(admin.SimpleListFilter):
    title = "когда"
    parameter_name = "when"

    def lookups(self, request, model_admin):
        return [("upcoming", "Предстоящие"), ("past", "Прошедшие"), ("all", "Все")]

    def choices(self, changelist):
        # «Предстоящие» is the default, so it is marked when nothing is chosen
        for choice in super().choices(changelist):
            if choice["display"] == "All":
                continue
            yield choice

    def value(self):
        return super().value() or "upcoming"

    def queryset(self, request, queryset):
        today = timezone.localdate()
        if self.value() == "upcoming":
            return queryset.filter(start_date__gte=today)
        if self.value() == "past":
            return queryset.filter(start_date__lt=today)
        return queryset


@admin.register(Departure)
class DepartureAdmin(ModelAdmin):
    """Schedule: seats, price and notes are edited right in the list; «Запланировать» adds many."""

    list_display = [
        "dates",
        "tour",
        "weekdays",
        "seats_left",
        "price",
        "note",
        "status",
        "requests",
    ]
    list_display_links = ["dates"]
    list_editable = ["seats_left", "price", "note"]
    list_filter = [WhenFilter, "tour", "status"]
    list_filter_submit = True
    date_hierarchy = "start_date"
    list_per_page = 100
    actions = ["copy_next_year", "mark_full", "mark_open"]
    actions_list = ["plan"]
    fields = ["tour", ("start_date", "end_date"), ("seats_left", "status"), ("price", "note")]
    readonly_fields = ["end_date"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("tour")
            .annotate(_requests=Count("inquiries"))
        )

    @display(description="даты", ordering="start_date")
    def dates(self, obj):
        return obj.dates_label

    @display(description="дни недели")
    def weekdays(self, obj):
        return obj.weekdays_label

    @display(description="заявок", ordering="_requests")
    def requests(self, obj):
        return obj._requests or "—"

    def _mark(self, request, queryset, status):
        updated = queryset.update(status=status)
        self.message_user(request, f"Обновлено выездов: {updated}.")

    @admin.action(description="Есть места")
    def mark_open(self, request, queryset):
        self._mark(request, queryset, DepartureStatus.OPEN)

    @admin.action(description="Мест нет")
    def mark_full(self, request, queryset):
        self._mark(request, queryset, DepartureStatus.FULL)

    @admin.action(description="Скопировать на следующий год (тот же день недели)")
    def copy_next_year(self, request, queryset):
        from datetime import timedelta

        created = 0
        for departure in queryset.select_related("tour"):
            day = departure.start_date + timedelta(weeks=52)
            _, made = Departure.objects.get_or_create(
                tour=departure.tour,
                start_date=day,
                defaults={
                    "seats_left": departure.tour.group_size_max,
                    "price": departure.price,
                    "note": departure.note,
                },
            )
            created += made
        self.message_user(request, f"Добавлено выездов на следующий год: {created}.")

    @action(description="Запланировать даты", url_path="plan", icon="event_repeat")
    def plan(self, request):
        """Step 1: tour, first date, how often. Step 2: the list of dates to confirm."""
        initial = {"tour": request.GET.get("tour")}
        form = DeparturePlanForm(request.POST or None, initial=initial)
        days = None
        if request.method == "POST" and form.is_valid():
            tour = form.cleaned_data["tour"]
            days = form.cleaned_data["days"]
            if "confirm" in request.POST:
                created, skipped = create_departures(
                    tour, days, seats_left=form.cleaned_data["seats_left"]
                )
                note = f" Уже были в расписании: {skipped}." if skipped else ""
                messages.success(request, f"«{tour}»: добавлено выездов — {created}.{note}")
                return redirect(
                    reverse("admin:tours_departure_changelist") + f"?tour__id__exact={tour.pk}"
                )
            existing = set(
                tour.departures.filter(start_date__in=days).values_list("start_date", flat=True)
            )
            days = [
                {
                    "start": d,
                    "end": d + timedelta(days=tour.duration_days - 1),
                    "exists": d in existing,
                }
                for d in days
            ]
        context = {
            **self.admin_site.each_context(request),
            "title": "Запланировать даты выездов",
            "form": form,
            "days": days,
            "new_count": sum(not d["exists"] for d in days or []),
            "opts": self.model._meta,
        }
        return TemplateResponse(request, "admin/tours/departure_plan.html", context)
