"""A year of demo dates for the group tours, so the calendar has something to show.

Replaces the dates of the demo tours only (by slug); a real tour's calendar is never touched.
"""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.tours.models import Departure, DepartureStatus, Tour, TourType
from apps.tours.services.departures import create_departures, repeat_dates

DEMO_SLUGS = {
    "ala-kul-trek": 7,
    "song-kul-yurts": 10,
    "song-kul-horse-trek": 14,
    "winter-karakol": 14,
}


class Command(BaseCommand):
    help = "Demo calendar: a year of dates for the demo group tours."

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(2027)
        today = timezone.localdate()
        total = 0
        for tour in Tour.objects.filter(slug__in=DEMO_SLUGS, tour_type=TourType.GROUP):
            Departure.objects.filter(tour=tour).delete()
            # the first Saturday from next week, then every N days within the season
            first = today + timedelta(days=7 + (5 - today.weekday()) % 7)
            days = repeat_dates(
                first,
                DEMO_SLUGS[tour.slug],
                today + timedelta(days=365),
                (tour.season_start, tour.season_end),
            )
            create_departures(tour, days, seats_left=tour.group_size_max or 10)
            # the nearest dates fill up first
            for i, departure in enumerate(tour.departures.order_by("start_date")[:6]):
                if i == 0:
                    departure.status, departure.seats_left = DepartureStatus.FEW, 2
                elif random.random() < 0.3:
                    departure.status, departure.seats_left = DepartureStatus.FULL, 0
                else:
                    departure.seats_left = random.randint(3, departure.seats_left or 8)
                departure.save()
            total += len(days)
        self.stdout.write(self.style.SUCCESS(f"Demo calendar: {total} departures."))
