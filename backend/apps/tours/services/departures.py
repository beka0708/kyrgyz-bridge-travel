"""Planning tour dates for a whole season at once (admin: «Расписание выездов → Запланировать»)."""

import re
from datetime import date, timedelta

from django.core.exceptions import ValidationError

from apps.tours.models import Departure, DepartureStatus, Tour


def in_season(day: date, start_month: int | None, end_month: int | None) -> bool:
    """Season May–Oct, or one that wraps the new year (Dec–Mar)."""
    if not start_month or not end_month:
        return True
    if start_month <= end_month:
        return start_month <= day.month <= end_month
    return day.month >= start_month or day.month <= end_month


def repeat_dates(
    first: date, every_days: int, until: date, season: tuple[int | None, int | None] = (None, None)
) -> list[date]:
    if every_days < 1:
        raise ValidationError("Интервал — минимум 1 день.")
    days, day = [], first
    while day <= until:
        if in_season(day, *season):
            days.append(day)
        day += timedelta(days=every_days)
    return days


_DATE = re.compile(r"(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?")


def parse_dates(text: str, today: date) -> list[date]:
    """«14.06, 21.06.2027, 5/7» → dates; without a year: the next such date from today."""
    days = []
    for d, m, y in _DATE.findall(text):
        try:
            if y:
                year = int(y) + (2000 if len(y) == 2 else 0)
                days.append(date(year, int(m), int(d)))
            else:
                candidate = date(today.year, int(m), int(d))
                days.append(
                    candidate if candidate >= today else candidate.replace(year=today.year + 1)
                )
        except ValueError as exc:
            raise ValidationError(f"Не понял дату «{d}.{m}{'.' + y if y else ''}».") from exc
    return sorted(set(days))


def create_departures(
    tour: Tour, days: list[date], status=DepartureStatus.OPEN, seats_left=None
) -> tuple[int, int]:
    """Adds the dates the tour does not have yet. Returns (created, skipped)."""
    existing = set(tour.departures.filter(start_date__in=days).values_list("start_date", flat=True))
    created = 0
    for day in days:
        if day in existing:
            continue
        Departure.objects.create(tour=tour, start_date=day, status=status, seats_left=seats_left)
        created += 1
    return created, len(days) - created


def by_month(departures) -> list[dict]:
    """[{"key": "2027-06", "label": "Jun 2027", "short": "Jun", "items": [...]}, ...]"""
    months: dict[str, dict] = {}
    for departure in departures:
        start = departure.start_date
        key = f"{start:%Y-%m}"
        if key not in months:
            months[key] = {
                "key": key,
                "label": f"{start:%b %Y}",
                "short": f"{start:%b}",
                "items": [],
            }
        months[key]["items"].append(departure)
    return list(months.values())
