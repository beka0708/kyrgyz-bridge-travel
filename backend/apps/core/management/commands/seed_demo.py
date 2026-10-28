"""Demo content for local development and frontend work. Safe to run repeatedly."""

import io
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image, ImageDraw

from apps.content.models import FAQ, Guide, Review, Stat
from apps.core.models import SiteSettings
from apps.tours.models import Difficulty, ListKind, Tour, TourType

# Approximate coordinates, good enough for map development.
BISHKEK = (42.8746, 74.5698, "Bishkek")
KARAKOL = (42.4907, 78.3936, "Karakol")
ALTYN_ARASHAN = (42.3747, 78.6186, "Altyn-Arashan")
ALA_KUL = (42.2846, 78.5203, "Ala-Kul lake")
JETI_OGUZ = (42.3283, 78.2350, "Jeti-Oguz")
CHOLPON_ATA = (42.6495, 77.0855, "Cholpon-Ata")
SKAZKA = (42.1530, 77.3570, "Skazka canyon")
KOCHKOR = (42.2150, 75.7550, "Kochkor")
SONG_KUL = (41.8300, 75.1300, "Song-Kul lake")
ARSLANBOB = (41.3330, 72.9330, "Arslanbob")
JALAL_ABAD = (40.9333, 73.0000, "Jalal-Abad")

TOURS = [
    {
        "slug": "ala-kul-trek",
        "title": "Ala-Kul Lake Trek",
        "tour_type": TourType.GROUP,
        "short_description": "Turquoise alpine lake, hot springs and a 3,900 m pass.",
        "price_from": Decimal("390"),
        "duration_days": 4,
        "difficulty": Difficulty.HARD,
        "group": (4, 10),
        "season": (6, 9),
        "featured": True,
        "color": (46, 74, 62),
        "days": [
            ("Bishkek — Karakol", [BISHKEK, CHOLPON_ATA, KARAKOL], "road"),
            ("Up to Altyn-Arashan valley", [KARAKOL, ALTYN_ARASHAN], "hiking"),
            ("Ala-Kul lake and the pass", [ALTYN_ARASHAN, ALA_KUL], "hiking"),
            ("Down to Karakol", [ALA_KUL, KARAKOL], "hiking"),
        ],
    },
    {
        "slug": "issyk-kul-canyons",
        "title": "Issyk-Kul: Shores and Canyons",
        "tour_type": TourType.SOLO,
        "short_description": "The warm side of the lake, red canyons and the Seven Bulls rocks.",
        "price_from": Decimal("290"),
        "duration_days": 3,
        "difficulty": Difficulty.EASY,
        "group": (1, 6),
        "season": (5, 10),
        "featured": True,
        "color": (34, 86, 120),
        "days": [
            ("Bishkek — Cholpon-Ata", [BISHKEK, CHOLPON_ATA], "road"),
            ("Skazka canyon", [CHOLPON_ATA, SKAZKA], "road"),
            ("Jeti-Oguz and back", [SKAZKA, JETI_OGUZ, KARAKOL], "road"),
        ],
    },
    {
        "slug": "song-kul-yurts",
        "title": "Song-Kul: Nights in a Yurt",
        "tour_type": TourType.GROUP,
        "short_description": "Nomad life at 3,000 m: horses, yurts and a sky full of stars.",
        "price_from": Decimal("320"),
        "duration_days": 3,
        "difficulty": Difficulty.MODERATE,
        "group": (2, 8),
        "season": (6, 9),
        "featured": True,
        "color": (120, 84, 40),
        "days": [
            ("Bishkek — Kochkor", [BISHKEK, KOCHKOR], "road"),
            ("Kochkor — Song-Kul", [KOCHKOR, SONG_KUL], "road"),
            ("Song-Kul — Bishkek", [SONG_KUL, KOCHKOR, BISHKEK], "road"),
        ],
    },
    {
        "slug": "arslanbob-walnut-forest",
        "title": "Arslanbob: Walnut Forest and Waterfalls",
        "tour_type": TourType.SOLO,
        "short_description": "The world's largest walnut forest and two waterfalls in the south.",
        "price_from": Decimal("350"),
        "duration_days": 4,
        "difficulty": Difficulty.MODERATE,
        "group": (1, 6),
        "season": (5, 10),
        "featured": False,
        "color": (70, 100, 50),
        "days": [
            ("Flight to Jalal-Abad", [BISHKEK, JALAL_ABAD], "manual"),
            ("Jalal-Abad — Arslanbob", [JALAL_ABAD, ARSLANBOB], "road"),
            ("Big and small waterfalls", [ARSLANBOB], "manual"),
            ("Back to Bishkek", [ARSLANBOB, JALAL_ABAD, BISHKEK], "manual"),
        ],
    },
]

LIST_ITEMS = {
    ListKind.INCLUDED: ["English-speaking guide", "Transport", "Accommodation", "Meals on route"],
    ListKind.EXCLUDED: ["International flights", "Travel insurance", "Tips"],
    ListKind.GEAR: ["Hiking boots", "Warm jacket", "Sunglasses and sunscreen", "Headlamp"],
}


def placeholder_image(label, color, size=(1600, 1000)):
    """Plain colored JPEG with a caption; real photos come from the client."""
    img = Image.new("RGB", size, color)
    ImageDraw.Draw(img).text((40, 40), label, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    return ContentFile(buf.getvalue(), name=f"{label.lower().replace(' ', '-')[:40]}.jpg")


def waypoints(points):
    return [{"lat": lat, "lng": lng, "name": name} for lat, lng, name in points]


def straight_track(points):
    if len(points) < 2:
        return None
    return {"type": "LineString", "coordinates": [[lng, lat] for lat, lng, _ in points]}


class Command(BaseCommand):
    help = "Create demo tours, days, reviews and FAQ for local development."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete demo tours first.")

    @transaction.atomic
    def handle(self, *args, reset, **options):
        if reset:
            Tour.objects.filter(slug__in=[t["slug"] for t in TOURS]).delete()

        settings_obj = SiteSettings.load()
        if not settings_obj.whatsapp:
            settings_obj.brand_name = "Kyrgyz Tours"
            settings_obj.tagline = "Mountains, lakes and yurts"
            settings_obj.whatsapp = "996555000000"
            settings_obj.phone = "+996 555 000 000"
            settings_obj.email = "hello@example.com"
            settings_obj.inquiry_email = "inquiries@example.com"
            settings_obj.save()

        created = 0
        for order, data in enumerate(TOURS):
            if Tour.objects.filter(slug=data["slug"]).exists():
                continue
            tour = Tour.objects.create(
                slug=data["slug"],
                title=data["title"],
                tour_type=data["tour_type"],
                short_description=data["short_description"],
                description=f"[Full description of {data['title']} from the client.]",
                how_to_get_there="[How to get there: airport, meeting point, transfer.]",
                price_from=data["price_from"],
                price_note="per person",
                duration_days=data["duration_days"],
                difficulty=data["difficulty"],
                group_size_min=data["group"][0],
                group_size_max=data["group"][1],
                season_start=data["season"][0],
                season_end=data["season"][1],
                is_featured=data["featured"],
                order=order,
                cover=placeholder_image(data["title"], data["color"]),
            )
            for n in range(1, 4):
                tour.images.create(
                    image=placeholder_image(f"{data['title']} {n}", data["color"]),
                    alt=f"{data['title']} photo {n}",
                    order=n,
                )
            for kind, items in LIST_ITEMS.items():
                for i, text in enumerate(items):
                    tour.list_items.create(kind=kind, text=text, order=i)
            for number, (title, points, source) in enumerate(data["days"], start=1):
                day = tour.days.create(
                    day_number=number,
                    title=title,
                    description=f"[Day {number}: route, time on the way, overnight.]",
                    travel_time="5–6 h",
                    overnight="Guesthouse",
                    waypoints=waypoints(points),
                    track=straight_track(points),
                    track_source=source,
                )
                day.images.create(
                    image=placeholder_image(f"Day {number} {title}", data["color"], (1200, 800)),
                    alt=title,
                )
            created += 1

        if not Review.objects.exists():
            for i, (name, country) in enumerate(
                [("Anna", "Germany"), ("James", "UK"), ("Léa", "France")]
            ):
                Review.objects.create(
                    author_name=name,
                    country=country,
                    rating=5,
                    text="[Review text from the client.]",
                    tour=Tour.objects.order_by("order").first(),
                    order=i,
                )
        if not FAQ.objects.exists():
            for i, q in enumerate(
                ["Do I need a visa?", "Is it safe to travel?", "What is the best season?"]
            ):
                FAQ.objects.create(question=q, answer="[Answer from the client.]", order=i)
        if not Guide.objects.exists():
            for i, name in enumerate(["Aibek", "Nurlan"]):
                Guide.objects.create(
                    name=name,
                    role="Mountain guide",
                    languages="EN, RU, KG",
                    photo=placeholder_image(name, (60, 60, 60), (600, 600)),
                    order=i,
                )
        if not Stat.objects.exists():
            for i, (value, suffix, label) in enumerate(
                [
                    (10, "+", "years in the mountains"),
                    (3000, "+", "happy guests"),
                    (25, "", "routes"),
                ]
            ):
                Stat.objects.create(value=value, suffix=suffix, label=label, order=i)

        self.stdout.write(self.style.SUCCESS(f"Demo data ready, new tours: {created}"))
