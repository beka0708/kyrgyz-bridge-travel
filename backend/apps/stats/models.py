"""First-party counters for the admin dashboard: no cookies, no personal data, one row per day.

Google Analytics covers traffic in depth; these answer «which tours are looked at» and «how many
people tap WhatsApp» (WhatsApp leads never reach our database otherwise).
"""

from django.db import models


class TourView(models.Model):
    tour = models.ForeignKey(
        "tours.Tour", verbose_name="тур", on_delete=models.CASCADE, related_name="daily_views"
    )
    date = models.DateField("день", db_index=True)
    views = models.PositiveIntegerField("просмотры", default=0)

    class Meta:
        verbose_name = "просмотры тура за день"
        verbose_name_plural = "просмотры туров"
        constraints = [models.UniqueConstraint(fields=["tour", "date"], name="tourview_per_day")]

    def __str__(self):
        return f"{self.tour} {self.date}: {self.views}"


class ContactChannel(models.TextChoices):
    WHATSAPP = "whatsapp", "WhatsApp"
    PHONE = "phone", "Звонок"
    EMAIL = "email", "Email"


class ContactClick(models.Model):
    date = models.DateField("день", db_index=True)
    channel = models.CharField("канал", max_length=10, choices=ContactChannel.choices)
    clicks = models.PositiveIntegerField("нажатия", default=0)

    class Meta:
        verbose_name = "нажатия на контакты за день"
        verbose_name_plural = "нажатия на контакты"
        constraints = [models.UniqueConstraint(fields=["date", "channel"], name="click_per_day")]

    def __str__(self):
        return f"{self.get_channel_display()} {self.date}: {self.clicks}"


class CountryVisit(models.Model):
    """Visitors per country per day (one per visitor and day, from the IP; the IP is not kept)."""

    date = models.DateField("день", db_index=True)
    country = models.CharField(
        "страна", max_length=2, blank=True, help_text="ISO-код, пусто — не определена"
    )
    visits = models.PositiveIntegerField("посетители", default=0)

    class Meta:
        verbose_name = "посетители по странам за день"
        verbose_name_plural = "посетители по странам"
        constraints = [
            models.UniqueConstraint(fields=["date", "country"], name="countryvisit_per_day")
        ]

    def __str__(self):
        return f"{self.country or '??'} {self.date}: {self.visits}"
