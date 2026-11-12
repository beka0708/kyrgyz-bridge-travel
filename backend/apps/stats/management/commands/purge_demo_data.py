"""Remove the demo activity before handing the site over: demo inquiries and dashboard numbers.

    manage.py purge_demo_data --stats-until 2026-11-10          # shows what would go
    manage.py purge_demo_data --stats-until 2026-11-10 --yes    # deletes it

Demo inquiries are recognised by their mark (utm_campaign, or user_agent in early demos, is
«demo-stats»), so real ones stay.
Daily counters (tour views, WhatsApp taps, countries) carry no mark: everything up to and
including --stats-until is removed. Tours, reviews, guides and the calendar are not touched.
"""

from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.inquiries.models import Inquiry
from apps.stats.management.commands.demo_stats import DEMO_MARK
from apps.stats.models import ContactClick, CountryVisit, TourView


class Command(BaseCommand):
    help = "Delete demo inquiries and the demo dashboard numbers (dry run without --yes)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--stats-until",
            required=True,
            help="Last day of demo statistics, YYYY-MM-DD (usually the launch day).",
        )
        parser.add_argument("--yes", action="store_true", help="Really delete.")

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            until = date.fromisoformat(options["stats_until"])
        except ValueError as exc:
            raise CommandError("--stats-until must look like 2026-11-10") from exc
        demo = Q(utm_campaign=DEMO_MARK) | Q(user_agent=DEMO_MARK)
        targets = {
            "demo inquiries": Inquiry.objects.filter(demo),
            "tour view days": TourView.objects.filter(date__lte=until),
            "contact tap days": ContactClick.objects.filter(date__lte=until),
            "country days": CountryVisit.objects.filter(date__lte=until),
        }
        for label, qs in targets.items():
            self.stdout.write(f"{label}: {qs.count()}")
        others = Inquiry.objects.exclude(demo)
        self.stdout.write(f"other inquiries (kept): {others.count()}")
        for inquiry in others.order_by("created_at")[:20]:
            self.stdout.write(
                f"  kept: {inquiry.created_at:%Y-%m-%d} {inquiry.name}, {inquiry.tour_title or '-'}"
            )
        if not options["yes"]:
            self.stdout.write(self.style.WARNING("Dry run: nothing deleted. Add --yes to delete."))
            return
        for qs in targets.values():
            qs.delete()
        self.stdout.write(self.style.SUCCESS("Demo inquiries and statistics deleted."))
