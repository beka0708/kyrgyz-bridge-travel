from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display

from apps.core.admin import thumbnail

from .models import FAQ, Guide, Review, Stat

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


@admin.register(Review)
class ReviewAdmin(OrderedAdmin):
    list_display = ["author_name", "country", "stars", "tour", "source", "is_published"]
    list_filter = ["rating", "source", "tour", "is_published"]
    list_select_related = ["tour"]
    search_fields = ["author_name", "text"]
    autocomplete_fields = ["tour"]

    @display(description="оценка", ordering="rating")
    def stars(self, obj):
        return "★" * obj.rating


@admin.register(FAQ)
class FAQAdmin(OrderedAdmin):
    list_display = ["question", "is_published"]
    search_fields = ["question", "answer"]


@admin.register(Stat)
class StatAdmin(OrderedAdmin):
    list_display = ["label", "value", "suffix", "is_published"]
    list_editable = ["value", "suffix", "is_published"]
