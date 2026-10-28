from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.inquiries.models import Inquiry, InquiryStatus
from apps.inquiries.services import notify_about_inquiry


class Command(BaseCommand):
    help = "Retry email notifications for inquiries that were saved but not emailed (run by cron)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=3, help="Look back this many days.")

    def handle(self, *args, days, **options):
        pending = list(
            Inquiry.objects.filter(
                notified_at__isnull=True,
                created_at__gte=timezone.now() - timedelta(days=days),
            ).exclude(status=InquiryStatus.SPAM)
        )
        sent = sum(notify_about_inquiry(inquiry) for inquiry in pending)
        self.stdout.write(f"Sent {sent} of {len(pending)} pending notifications.")
