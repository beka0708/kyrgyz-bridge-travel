from django.contrib import admin, messages
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from .models import Inquiry, InquiryStatus
from .services import notify_about_inquiry


def new_inquiries_badge(request):
    """Sidebar badge with the number of unprocessed inquiries."""
    count = Inquiry.objects.filter(status=InquiryStatus.NEW).count()
    return count or None


@admin.register(Inquiry)
class InquiryAdmin(ModelAdmin):
    list_display = [
        "created_at",
        "name",
        "tour_title",
        "dates",
        "people",
        "contact_info",
        "country_flag",
        "status_label",
        "notified",
    ]
    list_display_links = ["created_at", "name"]
    list_filter = ["status", "tour", "country", "created_at"]
    search_fields = ["name", "email", "contact", "comment", "tour_title"]
    date_hierarchy = "created_at"
    list_per_page = 50
    actions = ["mark_in_progress", "mark_done", "mark_spam", "resend_notification"]
    readonly_fields = [
        "name",
        "email",
        "contact",
        "tour",
        "tour_title",
        "departure",
        "travel_when",
        "date_from",
        "date_to",
        "people",
        "comment",
        "created_at",
        "notified_at",
        "ip",
        "country",
        "user_agent",
        "page_url",
        "utm_source",
        "utm_medium",
        "utm_campaign",
    ]
    fieldsets = [
        (
            "Заявка",
            {
                "fields": [
                    ("name", "email", "contact"),
                    ("tour", "tour_title"),
                    "departure",
                    ("travel_when", "people"),
                    ("date_from", "date_to"),
                    "comment",
                ]
            },
        ),
        ("Обработка", {"fields": ["status", "manager_note"]}),
        (
            "Техническое",
            {
                "classes": ["collapse"],
                "fields": [
                    ("created_at", "notified_at"),
                    ("ip", "country", "user_agent"),
                    "page_url",
                    ("utm_source", "utm_medium", "utm_campaign"),
                ],
            },
        ),
    ]

    def has_add_permission(self, request):
        return False  # inquiries only come from the website form

    @display(description="когда")
    def dates(self, obj):
        if obj.travel_when:
            return obj.travel_when
        if not obj.date_from:
            return "—"
        end = f" – {obj.date_to:%d.%m}" if obj.date_to else ""
        return f"{obj.date_from:%d.%m.%Y}{end}"

    @display(description="страна", ordering="country")
    def country_flag(self, obj):
        from apps.stats.geo import country_name, flag

        return f"{flag(obj.country)} {country_name(obj.country)}" if obj.country else "—"

    @display(description="контакт", header=True)
    def contact_info(self, obj):
        return obj.email, obj.contact

    @display(
        description="статус",
        ordering="status",
        label={
            InquiryStatus.NEW: "warning",
            InquiryStatus.IN_PROGRESS: "info",
            InquiryStatus.DONE: "success",
            InquiryStatus.SPAM: "danger",
        },
    )
    def status_label(self, obj):
        return obj.status, obj.get_status_display()

    @display(description="письмо", boolean=True)
    def notified(self, obj):
        return obj.notified_at is not None

    def _set_status(self, request, queryset, status):
        updated = queryset.update(status=status)
        self.message_user(request, f"Обновлено заявок: {updated}")

    @action(description="Отметить «В работе»")
    def mark_in_progress(self, request, queryset):
        self._set_status(request, queryset, InquiryStatus.IN_PROGRESS)

    @action(description="Отметить «Обработана»")
    def mark_done(self, request, queryset):
        self._set_status(request, queryset, InquiryStatus.DONE)

    @action(description="Отметить как спам")
    def mark_spam(self, request, queryset):
        self._set_status(request, queryset, InquiryStatus.SPAM)

    @action(description="Отправить письмо повторно")
    def resend_notification(self, request, queryset):
        sent = sum(notify_about_inquiry(inquiry) for inquiry in queryset)
        level = messages.SUCCESS if sent == queryset.count() else messages.WARNING
        self.message_user(request, f"Отправлено писем: {sent} из {queryset.count()}", level)
