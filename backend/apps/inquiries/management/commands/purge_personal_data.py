"""Keep only the personal data we still need (see «How long we keep it» in the Privacy Policy).

- IP address and browser of requests: erased after 30 days (only needed against spam);
- spam: deleted after 30 days;
- requests: deleted after 3 years.
Runs every night from cron (deploy/crontab.example). Safe to run any time.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.inquiries.models import Inquiry, InquiryStatus

TECH_DATA_DAYS = 30
SPAM_DAYS = 30
INQUIRY_YEARS = 3


class Command(BaseCommand):
    help = "Erase IPs after 30 days, spam after 30 days and requests after 3 years."

    def handle(self, *args, **options):
        now = timezone.now()
        erased = (
            Inquiry.objects.filter(created_at__lt=now - timedelta(days=TECH_DATA_DAYS))
            .exclude(ip=None, user_agent="")
            .update(ip=None, user_agent="")
        )
        spam, _ = Inquiry.objects.filter(
            status=InquiryStatus.SPAM, created_at__lt=now - timedelta(days=SPAM_DAYS)
        ).delete()
        old, _ = Inquiry.objects.filter(
            created_at__lt=now - timedelta(days=365 * INQUIRY_YEARS)
        ).delete()
        self.stdout.write(
            f"IP/browser erased: {erased}, spam deleted: {spam}, old requests deleted: {old}"
        )
