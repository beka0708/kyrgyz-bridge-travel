"""Realistic English demo texts for the client presentation. Photos are never touched.

The client replaces all of this in the admin; numbers (km, metres, prices) are approximate.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.content.models import FAQ, Guide, Review, Stat
from apps.core.models import SiteSettings
from apps.tours.models import ListKind, Tour

TOURS = {
    "ala-kul-trek": {
        "next_departure": "July 12",
        "description": (
            "A classic Tien Shan trek from Karakol to one of the most beautiful lakes in Central "
            "Asia. We walk up the Arashan river to natural hot springs, cross the Ala-Kul pass at "
            "about 3,900 m and come down past glacier views to the Karakol valley.\n\n"
            "Good fitness and a few previous hikes are enough: we walk 5–7 hours a day with light "
            "backpacks, while horses carry tents and food."
        ),
        "how_to_get_there": (
            "We meet you at Manas airport or your hotel in Bishkek\n"
            "Transfer to Karakol (6–7 h) along the north shore of Issyk-Kul\n"
            "Return transfer to Bishkek on the last day"
        ),
        "days": [
            (
                "Transfer along Issyk-Kul with a swim stop, dinner and briefing in Karakol.",
                None,
                None,
                "6–7 h",
                "Guesthouse in Karakol",
            ),
            (
                "Walk up the Arashan valley through spruce forest to the hot springs.",
                "16",
                900,
                "5–6 h",
                "Yurt camp, Altyn-Arashan",
            ),
            (
                "Early start to the pass, first view of the turquoise lake from above.",
                "13",
                1100,
                "7–8 h",
                "Tents by Ala-Kul",
            ),
            (
                "Descent through the Karakol valley, farewell dinner in town.",
                "18",
                None,
                "6 h",
                "Guesthouse in Karakol",
            ),
        ],
    },
    "issyk-kul-canyons": {
        "next_departure": "Any day, May – October",
        "description": (
            "An easy private trip for families and anyone who wants Kyrgyzstan without long hikes. "
            "We explore the colourful Skazka «Fairy-tale» canyon, swim in the high-mountain lake "
            "and walk to the red Seven Bulls rocks of Jeti-Oguz."
        ),
        "how_to_get_there": "Pick-up from your hotel in Bishkek\nPrivate car with driver for all three days",
        "days": [
            (
                "Drive to Cholpon-Ata, petroglyph field and an evening by the lake.",
                None,
                None,
                "4 h",
                "Hotel on the north shore",
            ),
            (
                "Skazka canyon at sunrise, beach afternoon on the warm south shore.",
                "5",
                None,
                "3 h",
                "Yurt camp by the lake",
            ),
            ("Jeti-Oguz rocks and the Valley of Flowers, return to Bishkek.", "6", 200, "7 h", "—"),
        ],
    },
    "song-kul-yurts": {
        "next_departure": "August 3",
        "description": (
            "Three days with nomad families on the Song-Kul plateau at 3,000 m. Ride horses across "
            "summer pastures, help with milking, taste kymyz and sleep in a felt yurt under a sky "
            "full of stars."
        ),
        "how_to_get_there": "Group transfer from Bishkek via Kochkor\nNo riding experience needed",
        "days": [
            (
                "Kochkor village, felt-making workshop with local women.",
                None,
                None,
                "4 h",
                "Homestay in Kochkor",
            ),
            (
                "Drive over the Kalmak-Ashuu pass, horse ride to the yurt camp.",
                "12",
                400,
                "5 h",
                "Yurt by Song-Kul lake",
            ),
            (
                "Sunrise by the lake, return to Bishkek through the Naryn valley.",
                None,
                None,
                "6–7 h",
                "—",
            ),
        ],
    },
    "arslanbob-walnut-forest": {
        "next_departure": "September 20",
        "description": (
            "The south of Kyrgyzstan is a different country: Uzbek villages, bazaars and the "
            "largest walnut forest in the world. We hike to two waterfalls and stay with a local "
            "family in Arslanbob."
        ),
        "how_to_get_there": "Domestic flight Bishkek — Jalal-Abad (1 h)\nReturn flight on the last day",
        "days": [
            (
                "Morning flight to the south, plov lunch at the Jalal-Abad bazaar.",
                None,
                None,
                "1 h flight",
                "Hotel in Jalal-Abad",
            ),
            (
                "Drive up to Arslanbob, walk through the old walnut forest.",
                "8",
                300,
                "4 h",
                "Homestay in Arslanbob",
            ),
            (
                "Hike to the big 80-metre waterfall and the holy small one.",
                "14",
                700,
                "6 h",
                "Homestay in Arslanbob",
            ),
            ("Market morning in Jalal-Abad, flight back to Bishkek.", None, None, "3 h", "—"),
        ],
    },
}

LIST_ITEMS = {
    ListKind.INCLUDED: [
        "English-speaking local guide",
        "All transfers in a comfortable car",
        "Accommodation as in the programme",
        "Breakfasts and dinners on the route",
        "National park fees",
    ],
    ListKind.EXCLUDED: ["International flights", "Travel insurance", "Lunches in towns", "Tips"],
    ListKind.GEAR: [
        "Hiking boots that are already broken in",
        "Warm jacket and hat — nights are cold in the mountains",
        "Rain jacket",
        "Sunglasses and sunscreen",
        "Refillable water bottle",
    ],
}

FAQS = [
    (
        "Do I need a visa for Kyrgyzstan?",
        "Citizens of the EU, UK, USA, Canada, Australia and many other countries can stay up to 60 days without a visa. Check your passport is valid for at least 6 months.",
    ),
    (
        "Is it safe to travel in Kyrgyzstan?",
        "Yes. Kyrgyzstan is known for its hospitality, and in the mountains you are always with an experienced guide who knows the trails and the weather.",
    ),
    (
        "When is the best season?",
        "June to September for treks and Song-Kul; May to October for Issyk-Kul and the south. Snow on the high passes can stay until late June.",
    ),
    (
        "Can I travel alone?",
        "Of course. Choose a private tour, or join a group tour — many of our guests come on their own and leave with new friends.",
    ),
    (
        "How do I pay?",
        "No prepayment on the website. We confirm the dates in WhatsApp or by email, then you pay a 30% deposit by bank transfer and the rest on arrival.",
    ),
]

REVIEWS = [
    (
        "Anna",
        "Germany",
        "Ala-Kul was the highlight of our whole trip to Central Asia. Our guide knew every stone on the trail and made the hard pass day feel easy. The hot springs after the first day were pure magic.",
    ),
    (
        "James",
        "United Kingdom",
        "Perfectly organised from the airport pick-up to the last dinner. Small group, great food in the yurt camps and no stress at all — they handled everything.",
    ),
    (
        "Léa",
        "France",
        "We went to Song-Kul with two kids and it was unforgettable: horses, yurts, stars. The family who hosted us was so warm. We are already planning to come back.",
    ),
]

GUIDES = [
    (
        "Aibek",
        "Senior mountain guide",
        "These mountains are my home — I want you to feel at home here too.",
        "Born in Karakol, guiding treks in the Tien Shan for 12 years. Knows every trail around Ala-Kul and Altyn-Arashan, trained in wilderness first aid.",
        "EN, RU, KG",
        12,
    ),
    (
        "Nurlan",
        "Trekking and horse-riding guide",
        "The best view is always one more ridge away.",
        "Grew up with a nomad family on Song-Kul. Leads horse trips and cultural tours, and cooks the best plov on the road.",
        "EN, RU, KG",
        8,
    ),
]

ABOUT = (
    "We are a small team from Bishkek and Karakol. We started as mountain guides and still lead "
    "every trip ourselves — so you travel with people who live here, not with a call centre."
)


class Command(BaseCommand):
    help = (
        "Fill demo tours, FAQ, reviews and guides with realistic English texts (photos untouched)."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        updated = 0
        for slug, data in TOURS.items():
            tour = Tour.objects.filter(slug=slug).first()
            if not tour:
                continue
            tour.description = data["description"]
            tour.how_to_get_there = data["how_to_get_there"]
            tour.next_departure = data["next_departure"]
            tour.save()
            tour.list_items.all().delete()
            for kind, items in LIST_ITEMS.items():
                for i, text in enumerate(items):
                    tour.list_items.create(kind=kind, text=text, order=i)
            for day, (text, km, ascent, time, overnight) in zip(
                tour.days.order_by("day_number"), data["days"], strict=False
            ):
                day.description = text
                day.distance_km = Decimal(km) if km else None
                day.ascent_m = ascent
                day.travel_time = time
                day.overnight = "" if overnight == "—" else overnight
                day.save()
            updated += 1

        FAQ.objects.all().delete()
        for i, (question, answer) in enumerate(FAQS):
            FAQ.objects.create(question=question, answer=answer, order=i)

        tours = list(Tour.objects.order_by("order"))
        for i, (name, country, text) in enumerate(REVIEWS):
            Review.objects.update_or_create(
                author_name=name,
                defaults={
                    "country": country,
                    "text": text,
                    "rating": 5,
                    "order": i,
                    "tour": tours[i % len(tours)] if tours else None,
                },
            )

        for name, role, quote, bio, languages, years in GUIDES:
            Guide.objects.filter(name=name).update(
                role=role, quote=quote, bio=bio, languages=languages, experience_years=years
            )

        if not Stat.objects.exists():
            for i, (value, suffix, label) in enumerate(
                [
                    (12, "+", "years in the mountains"),
                    (3000, "+", "happy guests"),
                    (25, "", "routes"),
                ]
            ):
                Stat.objects.create(value=value, suffix=suffix, label=label, order=i)

        site = SiteSettings.load()
        if not site.about_text:
            site.about_text = ABOUT
            site.save()

        self.stdout.write(self.style.SUCCESS(f"Demo texts updated for {updated} tours."))
