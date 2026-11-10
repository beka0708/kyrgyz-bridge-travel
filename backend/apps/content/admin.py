from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from apps.core.admin import thumbnail

from .models import FAQ, Guide, Review, ReviewSource, Stat

# Not on the site since the redesign (kept in the database, hidden from the admin):
# Feature («Почему мы»), Season («Когда ехать»), Partner, GalleryPost («Живые кадры»).


class OrderedAdmin(ModelAdmin):
    """Drag-and-drop ordering and an inline «on site» toggle for all content lists."""

    ordering_field = "order"
    hide_ordering_field = True
    list_editable = ["is_published"]


@admin.register(Guide)
class GuideAdmin(OrderedAdmin):
    list_display = ["photo_preview", "name", "role", "languages", "is_published"]
    list_display_links = ["photo_preview", "name"]
    search_fields = ["name"]

    @display(description="")
    def photo_preview(self, obj):
        return thumbnail(obj.photo)


def pending_reviews_badge(request):
    """Sidebar badge: guest reviews from the site that nobody has published yet."""
    count = Review.objects.filter(source=ReviewSource.SITE, is_published=False).count()
    return count or None


@admin.register(Review)
class ReviewAdmin(OrderedAdmin):
    list_display = ["author_name", "country", "stars", "tour", "origin", "is_published"]
    list_filter = ["is_published", "source", "rating", "tour"]
    list_select_related = ["tour"]
    search_fields = ["author_name", "text", "email"]
    autocomplete_fields = ["tour"]
    actions = ["publish", "unpublish"]

    @display(description="оценка", ordering="rating")
    def stars(self, obj):
        return "★" * obj.rating + "☆" * (5 - obj.rating)

    @display(
        description="откуда",
        label={"new": "warning", "site": "info", "other": "success"},
    )
    def origin(self, obj):
        if obj.source == ReviewSource.SITE and not obj.is_published:
            return "new", "Новый, ждёт проверки"
        if obj.source == ReviewSource.SITE:
            return "site", "С сайта"
        return "other", obj.get_source_display()

    @action(description="Опубликовать на сайте")
    def publish(self, request, queryset):
        self.message_user(request, f"Опубликовано: {queryset.update(is_published=True)}")

    @action(description="Скрыть с сайта")
    def unpublish(self, request, queryset):
        self.message_user(request, f"Скрыто: {queryset.update(is_published=False)}")


@admin.register(FAQ)
class FAQAdmin(OrderedAdmin):
    list_display = ["question", "is_published"]
    search_fields = ["question", "answer"]


@admin.register(Stat)
class StatAdmin(OrderedAdmin):
    list_display = ["label", "value", "suffix", "is_published"]
    list_editable = ["value", "suffix", "is_published"]
