# ruff: noqa: E501 - demo copy reads better unwrapped
"""Fill the database like a live site: 8 tours with photos everywhere, guides, reviews, FAQ…

Demo only. Photos come from demo/photos/<key>.jpg (see fetch_demo_photos); when a photo is
missing, a local fallback pool (docs/design/photos) is used so the layout still looks full.
Safe to re-run: content is replaced, not duplicated.
"""

import hashlib
import io
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image, ImageDraw, ImageFont

from apps.content.models import FAQ, Feature, GalleryPost, Guide, Partner, Review, Season, Stat
from apps.core.models import SiteSettings
from apps.tours.models import Difficulty, Tour, TourType

REPO = Path(settings.REPO_DIR)
PHOTOS = REPO / "demo" / "photos"
FALLBACK = sorted((REPO / "docs" / "design" / "photos").glob("*.jp*g"))

# slug → photo group in demo/photos.json
PHOTO_GROUP = {
    "ala-kul-trek": "ala-kul",
    "issyk-kul-canyons": "issyk-kul",
    "song-kul-yurts": "song-kul",
    "arslanbob-walnut-forest": "arslanbob",
    "ala-archa-day-hike": "ala-archa",
    "song-kul-horse-trek": "horse-trek",
    "karakol-jeti-oguz": "jeti-oguz",
    "winter-karakol": "winter-karakol",
}

BISHKEK = (42.8746, 74.5698, "Bishkek")
ALA_ARCHA = (42.5636, 74.4836, "Ala-Archa park")
AK_SAI = (42.5250, 74.5050, "Ak-Sai waterfall")
KOCHKOR = (42.2150, 75.7550, "Kochkor")
KYZART = (41.9700, 75.0200, "Kyzart")
JAILOO = (41.9100, 75.0700, "Shepherds' jailoo")
SONG_KUL = (41.8300, 75.1300, "Song-Kul lake")
KARAKOL = (42.4907, 78.3936, "Karakol")
JETI_OGUZ = (42.3283, 78.2350, "Jeti-Oguz rocks")
KARAKOL_SKI = (42.4550, 78.4580, "Karakol ski base")
ALTYN_ARASHAN = (42.37316, 78.61103, "Altyn-Arashan")
CHOLPON_ATA = (42.6495, 77.0855, "Cholpon-Ata")

NEW_TOURS = [
    {
        "slug": "ala-archa-day-hike",
        "title": "Ala-Archa Gorge Day Hike",
        "tour_type": TourType.SOLO,
        "short_description": "Glaciers and juniper forest 40 minutes from Bishkek.",
        "description": (
            "The easiest way to stand under real Tien Shan glaciers. We drive 40 minutes from "
            "Bishkek into the national park and walk up the Ak-Sai gorge to a waterfall at "
            "3,300 m, with a picnic lunch on the way.\n\nPerfect on your first or last day."
        ),
        "how_to_get_there": "Pick-up from your hotel in Bishkek at 8:00\nBack in Bishkek around 18:00",
        "price": "79",
        "days_count": 1,
        "difficulty": Difficulty.EASY,
        "group": (1, 8),
        "season": (5, 10),
        "next": "Any day, May – October",
        "days": [
            (
                "Ala-Archa and the Ak-Sai waterfall",
                [BISHKEK, ALA_ARCHA, AK_SAI],
                "hiking",
                "Drive to the park, hike up the gorge to the waterfall, picnic and back.",
                "11",
                900,
                "6–7 h",
                "",
            ),
        ],
    },
    {
        "slug": "song-kul-horse-trek",
        "title": "Song-Kul Horse Trek",
        "tour_type": TourType.GROUP,
        "short_description": "Five days in the saddle across summer pastures to a lake at 3,000 m.",
        "description": (
            "A real nomad journey: we ride with local horsemen from Kyzart over two passes to "
            "Song-Kul, sleep in shepherds' yurts and eat what the families cook.\n\n"
            "No riding experience needed — the horses are calm and the pace is easy."
        ),
        "how_to_get_there": "Group transfer from Bishkek to Kyzart\nReturn transfer to Bishkek",
        "price": "590",
        "days_count": 5,
        "difficulty": Difficulty.MODERATE,
        "group": (3, 10),
        "season": (6, 9),
        "next": "21 June 2027",
        "days": [
            (
                "Bishkek — Kyzart",
                [BISHKEK, KOCHKOR, KYZART],
                "road",
                "Drive through the Boom gorge, meet the horsemen, first short ride.",
                None,
                None,
                "5 h",
                "Homestay in Kyzart",
            ),
            (
                "Over the first pass",
                [KYZART, JAILOO],
                "hiking",
                "Ride up through the pastures to the shepherds' summer camp.",
                "18",
                600,
                "5–6 h",
                "Shepherds' yurt",
            ),
            (
                "Down to Song-Kul",
                [JAILOO, SONG_KUL],
                "hiking",
                "Cross the Jalgyz-Karagai pass and see the lake open up below.",
                "20",
                500,
                "6 h",
                "Yurt camp by the lake",
            ),
            (
                "A day on the lake",
                [SONG_KUL],
                "manual",
                "Free day: ride along the shore, try kymyz, watch a kok-boru game.",
                None,
                None,
                "free",
                "Yurt camp by the lake",
            ),
            (
                "Back to Bishkek",
                [SONG_KUL, KOCHKOR, BISHKEK],
                "road",
                "Drive down through Kochkor, stop at a felt-making workshop.",
                None,
                None,
                "7 h",
                "",
            ),
        ],
    },
    {
        "slug": "karakol-jeti-oguz",
        "title": "Karakol & Jeti-Oguz Weekend",
        "tour_type": TourType.SOLO,
        "short_description": "Red rocks, a Dungan mosque and dinner with a local family.",
        "description": (
            "A relaxed two days around Karakol: the wooden Dungan mosque, the Sunday animal "
            "market, the red Seven Bulls rocks of Jeti-Oguz and the Valley of Flowers."
        ),
        "how_to_get_there": "Start in Karakol (we can arrange the transfer from Bishkek)",
        "price": "210",
        "days_count": 2,
        "difficulty": Difficulty.EASY,
        "group": (1, 6),
        "season": (5, 10),
        "next": "Any weekend, May – October",
        "days": [
            (
                "Karakol town and market",
                [KARAKOL],
                "manual",
                "Dungan mosque, Holy Trinity cathedral, ashlyan-fu lunch, dinner with a family.",
                "6",
                None,
                "4 h",
                "Guesthouse in Karakol",
            ),
            (
                "Jeti-Oguz and the Valley of Flowers",
                [KARAKOL, JETI_OGUZ],
                "road",
                "Walk around the red rocks and up to the Valley of Flowers viewpoint.",
                "8",
                400,
                "5 h",
                "",
            ),
        ],
    },
    {
        "slug": "winter-karakol",
        "title": "Winter in Karakol: Ski & Hot Springs",
        "tour_type": TourType.GROUP,
        "short_description": "Powder days on Karakol slopes and a soak in Altyn-Arashan hot springs.",
        "description": (
            "Kyrgyzstan in winter is empty, white and very affordable. Three days of skiing or "
            "snowboarding in Karakol, then a snowcat ride up to the hot springs of Altyn-Arashan."
        ),
        "how_to_get_there": "Group transfer from Bishkek airport\nSki and boot rental included",
        "price": "640",
        "days_count": 5,
        "difficulty": Difficulty.MODERATE,
        "group": (4, 10),
        "season": (12, 3),
        "next": "8 January 2027",
        "days": [
            (
                "Bishkek — Karakol",
                [BISHKEK, CHOLPON_ATA, KARAKOL],
                "road",
                "Drive along the frozen shore of Issyk-Kul.",
                None,
                None,
                "6–7 h",
                "Hotel in Karakol",
            ),
            (
                "Ski day 1",
                [KARAKOL, KARAKOL_SKI],
                "road",
                "Warm-up runs with a local instructor.",
                None,
                None,
                "full day",
                "Hotel in Karakol",
            ),
            (
                "Ski day 2",
                [KARAKOL_SKI],
                "manual",
                "Off-piste with a guide if the snow allows.",
                None,
                None,
                "full day",
                "Hotel in Karakol",
            ),
            (
                "Snowcat to Altyn-Arashan",
                [KARAKOL, ALTYN_ARASHAN],
                "manual",
                "Ride up the valley and soak in the hot springs under the stars.",
                "14",
                None,
                "3 h",
                "Hot-spring lodge",
            ),
            (
                "Back to Bishkek",
                [ALTYN_ARASHAN, KARAKOL, BISHKEK],
                "road",
                "Descend and drive back to Bishkek.",
                None,
                None,
                "8 h",
                "",
            ),
        ],
    },
]

NEXT_DEPARTURE = {
    "ala-kul-trek": "12 July 2027",
    "issyk-kul-canyons": "Any day, May – October",
    "song-kul-yurts": "3 August 2027",
    "arslanbob-walnut-forest": "20 September 2027",
}
FEATURED = {
    "ala-kul-trek",
    "song-kul-yurts",
    "song-kul-horse-trek",
    "issyk-kul-canyons",
    "winter-karakol",
}

FEATURES = [
    (
        "why-groups",
        "Up to 10 people per group",
        "The guide knows everyone by name, and we can change the plan when the weather changes.",
    ),
    (
        "why-guides",
        "Guides from these valleys",
        "They grew up here, speak English and carry a first-aid kit and a satellite phone on every trek.",
    ),
    (
        "why-booking",
        "Pay nothing to ask",
        "Send a request or message us. You pay a deposit only after we confirm your dates.",
    ),
    (
        "why-offtrack",
        "Quiet places, real homes",
        "Summer pastures, high passes and village homestays where a family cooks dinner for you.",
    ),
]

SEASONS = [
    (
        "season-june",
        "June – July",
        "Green pastures",
        "Wildflowers on the jailoo and nomads moving up with their herds.",
        "song-kul-horse-trek",
    ),
    (
        "season-august",
        "August",
        "Lakes at their warmest",
        "The best month for Song-Kul yurts and swimming in Issyk-Kul.",
        "song-kul-yurts",
    ),
    (
        "season-october",
        "September – October",
        "Golden autumn",
        "Yellow poplars, walnut harvest in Arslanbob and quiet trails.",
        "arslanbob-walnut-forest",
    ),
    (
        "season-winter",
        "December – March",
        "Snow and hot springs",
        "Empty slopes in Karakol and steaming springs in the mountains.",
        "winter-karakol",
    ),
]

GUIDES = [
    (
        "guide-aibek",
        "Aibek Toktogulov",
        "Senior mountain guide",
        12,
        "English, Russian, Kyrgyz",
        "These mountains are my home — I want you to feel at home here too.",
        "Born in Karakol. Has led Ala-Kul and Altyn-Arashan treks for 12 years. Wilderness First Responder (2023).",
    ),
    (
        "guide-aigerim",
        "Aigerim Sadykova",
        "Cultural guide & trip planner",
        6,
        "English, German, Russian, Kyrgyz",
        "Kyrgyz hospitality is the real highlight — I make sure you feel it.",
        "Studied tourism in Bishkek and Leipzig. Plans every trip and leads city and culture tours.",
    ),
    (
        "guide-nurlan",
        "Nurlan Abdyraev",
        "Horse-trek leader",
        8,
        "English, Russian, Kyrgyz",
        "The best view is always one more ridge away.",
        "Grew up with a nomad family on Song-Kul. Leads horse trips and cooks the best plov on the road.",
    ),
    (
        "guide-timur",
        "Timur Akmatov",
        "Trekking & ski guide",
        7,
        "English, Russian",
        "Good weather is a bonus, good company is the plan.",
        "Ski instructor in winter, trekking guide in summer. Knows every slope around Karakol.",
    ),
    (
        "guide-bakyt",
        "Bakyt ata",
        "Song-Kul host",
        30,
        "Kyrgyz, Russian",
        "A guest is a gift from God — come, sit, drink kymyz.",
        "Has spent thirty summers with his herds on Song-Kul. Hosts our guests in his family yurts.",
    ),
]

REVIEWS = [
    (
        "review-anna",
        "Anna K.",
        "Germany",
        "ala-kul-trek",
        "google",
        date(2026, 8, 14),
        "Ala-Kul was the highlight of our whole trip to Central Asia. Aibek knew every stone on the trail, "
        "kept us safe on the pass and still found time to show us edelweiss. The hot springs after the "
        "first day were pure magic.",
    ),
    (
        "review-james",
        "James P.",
        "United Kingdom",
        "song-kul-yurts",
        "tripadvisor",
        date(2026, 7, 22),
        "Perfectly organised from the airport pick-up to the last dinner. Small group, great food in the "
        "yurt camps and no stress at all — they handled everything, including my lost luggage.",
    ),
    (
        "review-lea",
        "Léa M.",
        "France",
        "song-kul-horse-trek",
        "google",
        date(2026, 7, 3),
        "We came with two kids (9 and 12) and it was unforgettable: horses, yurts, stars. The family who "
        "hosted us was so warm. We are already planning to come back in winter.",
    ),
    (
        "review-kenji",
        "Kenji S.",
        "Japan",
        "ala-archa-day-hike",
        "tripadvisor",
        date(2026, 9, 9),
        "A perfect first day in Kyrgyzstan. Easy to book on WhatsApp, the guide was on time and spoke "
        "very good English. The glacier views are incredible so close to the city.",
    ),
    (
        "review-sofia",
        "Sofia R.",
        "Italy",
        "issyk-kul-canyons",
        "google",
        date(2026, 6, 18),
        "Relaxed and beautiful. Skazka canyon at sunrise had no one else there. Aigerim answered all our "
        "questions before the trip within a few hours.",
    ),
    (
        "review-mark",
        "Mark D.",
        "United States",
        "winter-karakol",
        "google",
        date(2026, 2, 11),
        "Skiing in Karakol felt like a secret. Powder, no lines, and the hot springs at the end were the "
        "best recovery ever. Great value for money.",
    ),
]

FAQS = [
    (
        "Do I need a visa for Kyrgyzstan?",
        "Citizens of the EU, UK, USA, Canada, Australia, Japan and many other countries can stay up to 60 days without a visa. Your passport should be valid for at least 6 months.",
    ),
    (
        "Is it safe to travel in Kyrgyzstan?",
        "Yes. Kyrgyzstan is calm and famously hospitable. In the mountains you are always with an experienced guide who carries a first-aid kit and a satellite phone and checks the weather every morning.",
    ),
    (
        "When is the best season?",
        "June to September for treks, horse trips and Song-Kul; May to October for Issyk-Kul and the south; December to March for skiing in Karakol.",
    ),
    (
        "What about altitude sickness?",
        "Our routes climb slowly. The highest point on Ala-Kul is about 3,900 m; we plan rest stops and the guide watches for symptoms. Tell us about any health conditions when you book.",
    ),
    (
        "Can I travel alone?",
        "Of course. Choose a private tour, or join a group — many guests come on their own and leave with new friends. There is no single supplement in group yurts.",
    ),
    (
        "How do I pay?",
        "Asking is free. After we confirm your dates you pay a 30% deposit by card or bank transfer; the rest is paid on arrival in cash (USD, EUR or KGS) or by card.",
    ),
    (
        "What is the cancellation policy?",
        "Free cancellation up to 30 days before the start. Later, we keep the deposit, or you can move your trip to another date once for free.",
    ),
    (
        "What should I pack?",
        "Each tour page has a «What to bring» list. In short: broken-in boots, a warm layer, a rain jacket, sun protection and a refillable bottle.",
    ),
    (
        "Will I have internet?",
        "Towns have good 4G; buy a local SIM at the airport (about $5). In high camps there is usually no signal — a nice break.",
    ),
]

PARTNERS = [
    "Tien Shan Trekking Assoc.",
    "Silk Road Travel Network",
    "Nomad Hospitality",
    "Mountain Rescue KG",
    "Eco Tour Asia",
]

HOME_TEXT = {
    "hero_title": "Kyrgyzstan on foot, on horseback and *in a yurt*",
    "hero_subtitle": "Trek to Ala-Kul lake, sleep in a yurt on Song-Kul or take it easy around "
    "Issyk-Kul. Small groups, local guides, from $79.",
    "solo_text": "Your own guide, car and driver. You pick the dates and the pace. "
    "Good for couples, families and friends.",
    "group_text": "Fixed dates, up to 10 travellers and a lower price per person. "
    "Good if you travel alone.",
    "about_title": "A small team that *knows the mountains*",
    "about_text": "We are guides from Bishkek, Karakol and Song-Kul. We started by taking friends "
    "to our favourite places and still lead every trip ourselves — so you travel with people "
    "who live here, not with a call centre.",
    "trust_line": "Reply within 24 hours · No prepayment to ask · Free cancellation up to 30 days",
}


def _resize_jpeg(data: bytes, max_side: int) -> bytes:
    with Image.open(io.BytesIO(data)) as im:
        im = im.convert("RGB")
        im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        im.save(out, "JPEG", quality=84, optimize=True)
        return out.getvalue()


def photo(key: str, portrait: bool = False) -> ContentFile | None:
    path = PHOTOS / f"{key}.jpg"
    # Until every Unsplash photo is downloaded (50 API requests/hour), fill gaps from the ones
    # we already have, then from the mockup photos.
    pool = sorted(PHOTOS.glob("tour-*.jpg")) or FALLBACK
    if path.exists():
        data = path.read_bytes()
    elif pool:
        pick = int(hashlib.md5(key.encode()).hexdigest(), 16) % len(pool)
        data = _resize_jpeg(pool[pick].read_bytes(), 1000 if portrait else 2000)
    else:
        return None
    return ContentFile(data, name=f"{key}.jpg")


def set_image(obj, field: str, key: str, portrait: bool = False):
    content = photo(key, portrait)
    if content is None:
        return
    current = getattr(obj, field)
    if current:
        current.delete(save=False)
    getattr(obj, field).save(content.name, content, save=False)


def group_keys(group: str) -> list[str]:
    keys = sorted(p.stem for p in PHOTOS.glob(f"tour-{group}-*.jpg"))
    return keys or [f"tour-{group}-{i}" for i in range(5)]


def logo(text: str) -> ContentFile:
    """Text logo for a fictional partner (demo only)."""
    img = Image.new("RGBA", (640, 160), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 44)
    except OSError:
        font = ImageFont.load_default()
    draw.text((320, 80), text, fill=(243, 241, 234, 255), font=font, anchor="mm")
    out = io.BytesIO()
    img.save(out, "PNG")
    return ContentFile(
        out.getvalue(), name=f"partner-{hashlib.md5(text.encode()).hexdigest()[:6]}.png"
    )


class Command(BaseCommand):
    help = "Fill the site with demo content and photos (8 tours, guides, reviews, FAQ, seasons…)."

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("seed_demo", stdout=self.stdout)  # base 4 tours, texts, settings
        self.add_tours()
        self.fill_tours()
        self.fill_content()
        self.fill_site()
        self.stdout.write(self.style.SUCCESS("Demo site filled. Run warm_images for fast pages."))

    def add_tours(self):
        for order, data in enumerate(NEW_TOURS, start=10):
            tour, created = Tour.objects.update_or_create(
                slug=data["slug"],
                defaults={
                    "title": data["title"],
                    "tour_type": data["tour_type"],
                    "short_description": data["short_description"],
                    "description": data["description"],
                    "how_to_get_there": data["how_to_get_there"],
                    "price_from": Decimal(data["price"]),
                    "price_note": "per person",
                    "duration_days": data["days_count"],
                    "difficulty": data["difficulty"],
                    "group_size_min": data["group"][0],
                    "group_size_max": data["group"][1],
                    "season_start": data["season"][0],
                    "season_end": data["season"][1],
                    "next_departure": data["next"],
                    "order": order,
                },
            )
            tour.days.all().delete()
            for n, (title, pts, source, text, km, ascent, time, overnight) in enumerate(
                data["days"], 1
            ):
                track = (
                    {"type": "LineString", "coordinates": [[lng, lat] for lat, lng, _ in pts]}
                    if len(pts) > 1
                    else None
                )
                tour.days.create(
                    day_number=n,
                    title=title,
                    description=text,
                    distance_km=Decimal(km) if km else None,
                    ascent_m=ascent,
                    travel_time=time,
                    overnight=overnight,
                    waypoints=[{"lat": la, "lng": lo, "name": nm} for la, lo, nm in pts],
                    track=track,
                    track_source=source,
                )
            if created:
                from apps.core.management.commands.demo_texts import LIST_ITEMS

                for kind, items in LIST_ITEMS.items():
                    for i, text in enumerate(items):
                        tour.list_items.create(kind=kind, text=text, order=i)

    def fill_tours(self):
        for tour in Tour.objects.all():
            group = PHOTO_GROUP.get(tour.slug)
            if not group:
                continue
            keys = group_keys(group)
            set_image(tour, "cover", keys[0])
            tour.is_featured = tour.slug in FEATURED
            if tour.slug in NEXT_DEPARTURE:
                tour.next_departure = NEXT_DEPARTURE[tour.slug]
            tour.save()
            for img in tour.images.all():
                img.image.delete(save=False)
            tour.images.all().delete()
            for i, key in enumerate(keys[1:] + keys[:1]):
                content = photo(key)
                if content:
                    tour.images.create(image=content, alt=f"{tour.title}, photo {i + 1}", order=i)
            for d, day in enumerate(tour.days.order_by("day_number")):
                for img in day.images.all():
                    img.image.delete(save=False)
                day.images.all().delete()
                for j in range(2):
                    content = photo(keys[(d * 2 + j + 1) % len(keys)])
                    if content:
                        day.images.create(image=content, alt=day.title, order=j)

    def fill_content(self):
        tours = {t.slug: t for t in Tour.objects.all()}
        for model in (Feature, Season, Guide, Review, FAQ, Partner, GalleryPost):
            for obj in model.objects.all():
                for field in ("image", "photo", "logo"):
                    f = getattr(obj, field, None)
                    if f:
                        f.delete(save=False)
            model.objects.all().delete()

        for i, (key, title, text) in enumerate(FEATURES):
            obj = Feature(title=title, text=text, order=i)
            set_image(obj, "image", key)
            obj.save()
        for i, (key, months, title, text, slug) in enumerate(SEASONS):
            obj = Season(months=months, title=title, text=text, tour=tours.get(slug), order=i)
            set_image(obj, "image", key)
            obj.save()
        for i, (key, name, role, years, langs, quote, bio) in enumerate(GUIDES):
            obj = Guide(
                name=name,
                role=role,
                experience_years=years,
                languages=langs,
                quote=quote,
                bio=bio,
                order=i,
            )
            set_image(obj, "photo", key, portrait=True)
            obj.save()
        for i, (key, name, country, slug, source, when, text) in enumerate(REVIEWS):
            obj = Review(
                author_name=name,
                country=country,
                tour=tours.get(slug),
                source=source,
                travel_date=when,
                rating=5,
                text=text,
                order=i,
            )
            set_image(obj, "photo", key, portrait=True)
            obj.save()
        for i, (question, answer) in enumerate(FAQS):
            FAQ.objects.create(question=question, answer=answer, order=i)
        for i, name in enumerate(PARTNERS):
            Partner.objects.create(name=name, logo=logo(name), order=i)
        for i in range(8):
            obj = GalleryPost(caption="", order=i, link="https://instagram.com/")
            set_image(obj, "image", f"feed-{i}")
            obj.save()
        Stat.objects.all().delete()
        for i, (value, suffix, label) in enumerate(
            [
                (12, "+", "years in the mountains"),
                (3000, "+", "travellers since 2014"),
                (25, "", "routes"),
            ]
        ):
            Stat.objects.create(value=value, suffix=suffix, label=label, order=i)

    def fill_site(self):
        site = SiteSettings.load()
        for field, value in HOME_TEXT.items():
            setattr(site, field, value)
        site.telegram = site.telegram or "kyrgyztours_demo"
        site.instagram_url = site.instagram_url or "https://instagram.com/"
        site.address = site.address or "Chui Avenue 120, Bishkek"
        for field, key in [
            ("hero_image", "hero"),
            ("about_image", "about"),
            ("solo_image", "format-solo"),
            ("group_image", "format-group"),
            ("steps_image", "steps"),
            ("faq_image", "faq"),
            ("request_image", "request"),
            ("footer_image", "footer"),
        ]:
            set_image(site, field, key)
        site.save()
