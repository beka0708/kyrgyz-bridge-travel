from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel


class InquiryStatus(models.TextChoices):
    NEW = "new", "Новая"
    IN_PROGRESS = "in_progress", "В работе"
    DONE = "done", "Обработана"
    SPAM = "spam", "Спам"


class Inquiry(TimeStampedModel):
    name = models.CharField("имя", max_length=100)
    email = models.EmailField("email", blank=True)
    contact = models.CharField(
        "телефон / мессенджер", max_length=100, blank=True, help_text="WhatsApp, Telegram, телефон"
    )
    tour = models.ForeignKey(
        "tours.Tour",
        verbose_name="тур",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inquiries",
    )
    # Snapshot, so the inquiry stays readable if the tour is renamed or deleted.
    tour_title = models.CharField("тур (на момент заявки)", max_length=150, blank=True)
    travel_when = models.CharField(
        "когда примерно",
        max_length=100,
        blank=True,
        help_text="Как написал турист: «mid-July 2027»",
    )
    date_from = models.DateField("даты с", null=True, blank=True)
    date_to = models.DateField("даты по", null=True, blank=True)
    people = models.PositiveSmallIntegerField(
        "человек", default=1, validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    comment = models.TextField("комментарий", blank=True)

    status = models.CharField(
        "статус", max_length=20, choices=InquiryStatus.choices, default=InquiryStatus.NEW
    )
    manager_note = models.TextField("заметка менеджера", blank=True)
    notified_at = models.DateTimeField("письмо отправлено", null=True, blank=True)

    # Technical context, useful for spam handling and marketing attribution.
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.CharField("браузер", max_length=300, blank=True)
    page_url = models.URLField("страница", max_length=500, blank=True)
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "заявка"
        verbose_name_plural = "заявки"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return f"{self.name} — {self.tour_title or 'без тура'}"

    def save(self, *args, **kwargs):
        if self.tour and not self.tour_title:
            self.tour_title = self.tour.title
        super().save(*args, **kwargs)
