"""Admin home page: what happened on the site in the last 30 days, in numbers the agency can act on.

Everything is computed from our own data (inquiries, guest reviews, tour views, contact taps), so it
works without Google Analytics. GA covers traffic sources and visitors in depth.
"""

import json
from datetime import timedelta

from django.db.models import Avg, Count, Q, Sum
from django.urls import reverse
from django.utils import timezone

from apps.content.models import Review, ReviewSource
from apps.inquiries.models import Inquiry, InquiryStatus
from apps.tours.models import Tour, TourType

from .geo import country_name, flag
from .models import ContactChannel, ContactClick, CountryVisit, TourView

PERIOD = 30
STATUS_COLORS = {
    InquiryStatus.NEW: "#f2994a",
    InquiryStatus.IN_PROGRESS: "#3b82f6",
    InquiryStatus.DONE: "#2fa564",
    InquiryStatus.SPAM: "#9ca3af",
}


def _pct(part, whole):
    return round(part * 100 / whole) if whole else 0


def _delta(current, previous):
    """+25 / -10 (percent change), or None when there is nothing to compare with."""
    if not previous:
        return None
    return round((current - previous) * 100 / previous)


def _kpi(title, value, *, previous=None, current=None, hint="", href="", suffix=""):
    return {
        "title": title,
        "value": value,
        "suffix": suffix,
        "delta": _delta(current if current is not None else value, previous)
        if previous is not None
        else None,
        "hint": hint,
        "href": href,
    }


def dashboard_callback(request, context):
    today = timezone.localdate()
    start = today - timedelta(days=PERIOD - 1)
    prev_start = start - timedelta(days=PERIOD)
    prev_end = start - timedelta(days=1)

    real = Inquiry.objects.exclude(status=InquiryStatus.SPAM)
    inquiries = real.filter(created_at__date__gte=start)
    inquiries_prev = real.filter(created_at__date__range=(prev_start, prev_end)).count()
    inquiry_count = inquiries.count()

    views = TourView.objects.filter(date__gte=start)
    view_total = views.aggregate(total=Sum("views"))["total"] or 0
    view_prev = (
        TourView.objects.filter(date__range=(prev_start, prev_end)).aggregate(total=Sum("views"))[
            "total"
        ]
        or 0
    )
    clicks = ContactClick.objects.filter(date__gte=start)
    wa_total = clicks.filter(channel=ContactChannel.WHATSAPP).aggregate(t=Sum("clicks"))["t"] or 0
    wa_prev = (
        ContactClick.objects.filter(
            date__range=(prev_start, prev_end), channel=ContactChannel.WHATSAPP
        ).aggregate(t=Sum("clicks"))["t"]
        or 0
    )
    leads = inquiry_count + wa_total

    admin_inquiries = reverse("admin:inquiries_inquiry_changelist")
    admin_reviews = reverse("admin:content_review_changelist")
    new_count = Inquiry.objects.filter(status=InquiryStatus.NEW).count()
    pending_reviews = Review.objects.filter(source=ReviewSource.SITE, is_published=False).count()

    kpis = [
        _kpi(
            "Заявки с сайта",
            inquiry_count,
            previous=inquiries_prev,
            hint="форма, без спама",
            href=admin_inquiries,
        ),
        _kpi("Нажали WhatsApp", wa_total, previous=wa_prev, hint="написали напрямую"),
        _kpi("Просмотры туров", view_total, previous=view_prev, hint="уникальные за день"),
        _kpi(
            "Конверсия в обращение",
            _pct(leads, view_total),
            current=_pct(leads, view_total),
            previous=_pct(inquiries_prev + wa_prev, view_prev) or None,
            suffix="%",
            hint="заявки + WhatsApp от просмотров туров",
        ),
    ]
    todo = [
        {
            "title": "Новые заявки без ответа",
            "value": new_count,
            "href": f"{admin_inquiries}?status__exact=new",
            "kind": "inquiries" if new_count else "done",
            "icon": "inbox",
        },
        {
            "title": "Отзывы ждут проверки",
            "value": pending_reviews,
            "href": f"{admin_reviews}?is_published__exact=0&source__exact=site",
            "kind": "reviews" if pending_reviews else "done",
            "icon": "star",
        },
    ]

    # --- daily chart: inquiries and WhatsApp taps (bars), tour views (line) ---------------
    days = [start + timedelta(days=i) for i in range(PERIOD)]
    per_day_inq = dict(
        inquiries.values_list("created_at__date")
        .annotate(n=Count("id"))
        .values_list("created_at__date", "n")
    )
    per_day_wa = dict(
        clicks.filter(channel=ContactChannel.WHATSAPP)
        .values_list("date")
        .annotate(n=Sum("clicks"))
        .values_list("date", "n")
    )
    per_day_views = dict(
        views.values_list("date").annotate(n=Sum("views")).values_list("date", "n")
    )
    chart = {
        "labels": [d.strftime("%d.%m") for d in days],
        "datasets": [
            {
                "type": "line",
                "label": "Просмотры туров",
                "data": [per_day_views.get(d, 0) for d in days],
                "borderColor": "#9ca3af",
                "backgroundColor": "#9ca3af",
                "yAxisID": "y1",
                "tension": 0.35,
                "pointRadius": 0,
                "borderWidth": 2,
            },
            {
                "label": "Заявки",
                "data": [per_day_inq.get(d, 0) for d in days],
                "backgroundColor": "#f2994a",
                "borderRadius": 4,
                "maxBarThickness": 14,
            },
            {
                "label": "WhatsApp",
                "data": [per_day_wa.get(d, 0) for d in days],
                "backgroundColor": "#25d366",
                "borderRadius": 4,
                "maxBarThickness": 14,
            },
        ],
    }
    chart_options = {
        "plugins": {"legend": {"display": True, "position": "bottom", "align": "start"}},
        "scales": {
            "y": {"beginAtZero": True, "ticks": {"precision": 0}, "position": "left"},
            "y1": {
                "beginAtZero": True,
                "position": "right",
                "grid": {"display": False},
                "ticks": {"precision": 0},
            },
            "x": {"grid": {"display": False}, "ticks": {"maxTicksLimit": 10}},
        },
    }

    # --- tours: interest and how often it turns into a request -------------------------
    tour_rows = []
    view_by_tour = dict(views.values_list("tour").annotate(n=Sum("views")).values_list("tour", "n"))
    inq_by_tour = dict(
        inquiries.exclude(tour=None)
        .values_list("tour")
        .annotate(n=Count("id"))
        .values_list("tour", "n")
    )
    top_views = max(view_by_tour.values(), default=0)
    for tour in Tour.objects.published().only("title", "slug", "tour_type"):
        v, q = view_by_tour.get(tour.pk, 0), inq_by_tour.get(tour.pk, 0)
        tour_rows.append(
            {
                "title": tour.title,
                "href": reverse("admin:tours_tour_change", args=[tour.pk]),
                "type": "Частный" if tour.tour_type == TourType.SOLO else "Группа",
                "views": v,
                "inquiries": q,
                "conversion": _pct(q, v),
                "bar": _pct(v, top_views),
            }
        )
    tour_rows.sort(key=lambda r: (-r["views"], -r["inquiries"]))
    no_tour = inquiries.filter(tour=None).count()

    # --- inquiries: statuses, sources, how people want to be contacted -----------------
    all_period = Inquiry.objects.filter(created_at__date__gte=start)
    status_counts = dict(
        all_period.values_list("status").annotate(n=Count("id")).values_list("status", "n")
    )
    status_total = sum(status_counts.values())
    statuses = [
        {
            "label": label,
            "value": status_counts.get(value, 0),
            "pct": _pct(status_counts.get(value, 0), status_total),
            "color": STATUS_COLORS[value],
        }
        for value, label in InquiryStatus.choices
    ]
    sources = []
    for source, n in (
        inquiries.values_list("utm_source")
        .annotate(n=Count("id"))
        .order_by("-n")
        .values_list("utm_source", "n")
    ):
        sources.append(
            {
                "label": source or "Без метки (поиск, прямой заход)",
                "value": n,
                "pct": _pct(n, inquiry_count),
            }
        )
    contact = inquiries.aggregate(
        both=Count("id", filter=~Q(email="") & ~Q(contact="")),
        email_only=Count("id", filter=~Q(email="") & Q(contact="")),
        phone_only=Count("id", filter=Q(email="") & ~Q(contact="")),
        people=Avg("people"),
    )
    contact_rows = [
        {
            "label": "Email и телефон",
            "value": contact["both"],
            "pct": _pct(contact["both"], inquiry_count),
        },
        {
            "label": "Только телефон / WhatsApp",
            "value": contact["phone_only"],
            "pct": _pct(contact["phone_only"], inquiry_count),
        },
        {
            "label": "Только email",
            "value": contact["email_only"],
            "pct": _pct(contact["email_only"], inquiry_count),
        },
    ]
    type_counts = inquiries.exclude(tour=None).aggregate(
        solo=Count("id", filter=Q(tour__tour_type=TourType.SOLO)),
        group=Count("id", filter=Q(tour__tour_type=TourType.GROUP)),
    )

    # --- where visitors come from (IP → country, DB-IP) ---------------------------------
    visits_by_country = dict(
        CountryVisit.objects.filter(date__gte=start)
        .values_list("country")
        .annotate(n=Sum("visits"))
        .values_list("country", "n")
    )
    inquiries_by_country = dict(
        inquiries.values_list("country").annotate(n=Count("id")).values_list("country", "n")
    )
    visitors_total = sum(visits_by_country.values())
    codes = sorted(
        set(visits_by_country) | set(inquiries_by_country),
        key=lambda c: (-visits_by_country.get(c, 0), -inquiries_by_country.get(c, 0), c == ""),
    )
    top_visits = max(visits_by_country.values(), default=0)
    country_rows = [
        {
            "flag": flag(code) if code else "🌐",
            "name": country_name(code),
            "visitors": visits_by_country.get(code, 0),
            "pct": _pct(visits_by_country.get(code, 0), visitors_total),
            "bar": _pct(visits_by_country.get(code, 0), top_visits),
            "inquiries": inquiries_by_country.get(code, 0),
        }
        for code in codes[:12]
    ]

    # --- guest reviews from the site ---------------------------------------------------
    site_reviews = Review.objects.filter(source=ReviewSource.SITE)
    review_stats = site_reviews.aggregate(avg=Avg("rating"), total=Count("id"))
    stars = dict(
        site_reviews.values_list("rating").annotate(n=Count("id")).values_list("rating", "n")
    )
    star_rows = [
        {"stars": s, "value": stars.get(s, 0), "pct": _pct(stars.get(s, 0), review_stats["total"])}
        for s in range(5, 0, -1)
    ]
    latest_reviews = site_reviews.select_related("tour").order_by("-created_at")[:4]

    context.update(
        {
            "period_days": PERIOD,
            "period_start": start,
            "kpis": kpis,
            "todo": todo,
            "chart_data": json.dumps(chart),
            "chart_options": json.dumps(chart_options),
            "tour_rows": tour_rows,
            "no_tour_inquiries": no_tour,
            "country_rows": country_rows,
            "visitors_total": visitors_total,
            "statuses": statuses,
            "status_total": status_total,
            "sources": sources,
            "contact_rows": contact_rows,
            "avg_people": round(contact["people"] or 0, 1),
            "type_split": {
                "solo": _pct(type_counts["solo"], type_counts["solo"] + type_counts["group"]),
                "group": _pct(type_counts["group"], type_counts["solo"] + type_counts["group"]),
            },
            "review_avg": round(review_stats["avg"] or 0, 1),
            "review_total": review_stats["total"],
            "star_rows": star_rows,
            "latest_reviews": latest_reviews,
            "admin_reviews": admin_reviews,
        }
    )
    return context
