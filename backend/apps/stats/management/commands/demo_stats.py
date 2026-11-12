"""Two months of demo activity for the admin dashboard: inquiries, tour views, WhatsApp taps.

Demo inquiries are marked (utm_campaign = DEMO_MARK) and replaced on every run; real data is never
touched. Only for previews: `make prod-demo` runs it after `demo_fill`.
"""

import random
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.inquiries.models import Inquiry, InquiryStatus
from apps.stats.models import ContactChannel, ContactClick, CountryVisit, TourView
from apps.tours.models import Tour

DEMO_MARK = "demo-stats"
DAYS = 60

NAMES = [
    ("Anna", "anna@example.com"),
    ("Lukas", "lukas@example.de"),
    ("Emma", ""),
    ("James", "james@example.co.uk"),
    ("Sophie", "sophie@example.fr"),
    ("Marco", ""),
    ("Yuki", "yuki@example.jp"),
    ("Olivia", "olivia@example.com"),
    ("Noah", ""),
    ("Clara", "clara@example.nl"),
    ("Ivan", "ivan@example.ru"),
    ("Mia", "mia@example.com"),
]
PHONES = [
    "+49 151 12345678",
    "+44 7700 900123",
    "+33 6 12 34 56 78",
    "+1 202 555 0147",
    "+81 90 1234 5678",
    "",
]
SOURCES = [("", 45), ("google", 25), ("instagram", 18), ("facebook", 8), ("tripadvisor", 4)]
# where foreign travellers to Kyrgyzstan come from (roughly)
COUNTRIES = [
    ("DE", 18),
    ("GB", 14),
    ("US", 12),
    ("FR", 9),
    ("KG", 8),
    ("RU", 7),
    ("KZ", 6),
    ("NL", 5),
    ("AU", 4),
    ("CH", 3),
    ("CA", 3),
    ("IL", 3),
    ("KR", 3),
    ("JP", 2),
    ("PL", 2),
    ("", 3),
]
WHEN = [
    "mid-July",
    "August, about a week",
    "early June",
    "September",
    "next summer",
    "December holidays",
    "",
]


def weighted(options):
    values, weights = zip(*options, strict=True)
    return random.choices(values, weights=weights)[0]


class Command(BaseCommand):
    help = "Fill the admin dashboard with two months of demo activity (preview only)."

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(2026)
        tours = list(Tour.objects.published())
        if not tours:
            self.stdout.write("No tours: run demo_fill first.")
            return
        today = timezone.localdate()
        Inquiry.objects.filter(utm_campaign=DEMO_MARK).delete()
        TourView.objects.filter(date__gte=today - timedelta(days=DAYS)).delete()
        ContactClick.objects.filter(date__gte=today - timedelta(days=DAYS)).delete()
        CountryVisit.objects.filter(date__gte=today - timedelta(days=DAYS)).delete()

        # Interest grows a little towards today (as if the ads started); bestsellers get more.
        popularity = {
            t.pk: (3.0 if t.is_featured else 1.0) * random.uniform(0.6, 1.4) for t in tours
        }
        views, clicks, visits, inquiries = [], [], [], 0
        for offset in range(DAYS, -1, -1):
            day = today - timedelta(days=offset)
            growth = 1 + (DAYS - offset) / DAYS  # 1 → 2
            weekend = 1.25 if day.weekday() >= 5 else 1.0
            for tour in tours:
                n = int(random.gauss(9, 3) * popularity[tour.pk] * growth * weekend)
                if n > 0:
                    views.append(TourView(tour=tour, date=day, views=n))
            people = max(5, int(random.gauss(38, 9) * growth * weekend))
            per_country: dict[str, int] = {}
            for _ in range(people):
                code = weighted(COUNTRIES)
                per_country[code] = per_country.get(code, 0) + 1
            visits += [CountryVisit(date=day, country=c, visits=n) for c, n in per_country.items()]
            wa = max(0, int(random.gauss(3, 1.5) * growth))
            if wa:
                clicks.append(ContactClick(date=day, channel=ContactChannel.WHATSAPP, clicks=wa))
            if random.random() < 0.25:
                clicks.append(ContactClick(date=day, channel=ContactChannel.EMAIL, clicks=1))

            for _ in range(max(0, int(random.gauss(1.1, 0.9) * growth))):
                inquiries += 1
                self._inquiry(day, offset, tours, popularity)

        TourView.objects.bulk_create(views)
        ContactClick.objects.bulk_create(clicks)
        CountryVisit.objects.bulk_create(visits)
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo stats: {inquiries} inquiries, {sum(v.views for v in views)} tour views, "
                f"{sum(c.clicks for c in clicks)} contact taps over {DAYS} days."
            )
        )

    def _inquiry(self, day, offset, tours, popularity):
        name, email = random.choice(NAMES)
        phone = random.choice(PHONES) if (not email or random.random() < 0.55) else ""
        if not email and not phone:
            phone = PHONES[0]
        tour = random.choices(tours + [None], weights=[popularity[t.pk] for t in tours] + [1.5])[0]
        # older inquiries are mostly handled, the last days are still new
        if offset <= 2:
            status = InquiryStatus.NEW
        elif offset <= 6:
            status = weighted([(InquiryStatus.NEW, 30), (InquiryStatus.IN_PROGRESS, 70)])
        else:
            status = weighted(
                [
                    (InquiryStatus.DONE, 70),
                    (InquiryStatus.IN_PROGRESS, 18),
                    (InquiryStatus.SPAM, 12),
                ]
            )
        source = weighted(SOURCES)
        inquiry = Inquiry.objects.create(
            name=name,
            email=email,
            contact=phone,
            tour=tour,
            tour_title=tour.title if tour else "",
            travel_when=random.choice(WHEN),
            people=weighted([(1, 15), (2, 45), (3, 12), (4, 18), (6, 10)]),
            status=status,
            utm_source=source,
            utm_medium="cpc" if source in ("google", "facebook") else ("social" if source else ""),
            utm_campaign=DEMO_MARK,
            country=weighted([c for c in COUNTRIES if c[0]]),
            user_agent="Mozilla/5.0 (demo)",
            notified_at=timezone.now(),
        )
        moment = timezone.make_aware(
            datetime.combine(day, time(random.randint(7, 23), random.randint(0, 59)))
        )
        Inquiry.objects.filter(pk=inquiry.pk).update(created_at=moment)
