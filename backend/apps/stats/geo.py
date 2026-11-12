"""Visitor country from the IP address, offline: the free DB-IP Lite database (CC BY 4.0).

The file is downloaded by `manage.py update_geoip` (monthly cron). Without it every visitor is
counted as «unknown», nothing breaks. The IP itself is never stored for statistics.
"""

import ipaddress
import logging
from functools import cache

from django.conf import settings

logger = logging.getLogger(__name__)

# Russian names for the admin; anything else falls back to phonenumbers' name, then the code.
COUNTRY_NAMES = {
    "KG": "Кыргызстан",
    "KZ": "Казахстан",
    "UZ": "Узбекистан",
    "TJ": "Таджикистан",
    "RU": "Россия",
    "BY": "Беларусь",
    "UA": "Украина",
    "TR": "Турция",
    "CN": "Китай",
    "IN": "Индия",
    "JP": "Япония",
    "KR": "Южная Корея",
    "SG": "Сингапур",
    "AE": "ОАЭ",
    "IL": "Израиль",
    "US": "США",
    "CA": "Канада",
    "MX": "Мексика",
    "BR": "Бразилия",
    "AU": "Австралия",
    "NZ": "Новая Зеландия",
    "GB": "Великобритания",
    "IE": "Ирландия",
    "DE": "Германия",
    "FR": "Франция",
    "NL": "Нидерланды",
    "BE": "Бельгия",
    "LU": "Люксембург",
    "CH": "Швейцария",
    "AT": "Австрия",
    "IT": "Италия",
    "ES": "Испания",
    "PT": "Португалия",
    "PL": "Польша",
    "CZ": "Чехия",
    "SK": "Словакия",
    "HU": "Венгрия",
    "RO": "Румыния",
    "BG": "Болгария",
    "GR": "Греция",
    "SE": "Швеция",
    "NO": "Норвегия",
    "DK": "Дания",
    "FI": "Финляндия",
    "EE": "Эстония",
    "LV": "Латвия",
    "LT": "Литва",
    "GE": "Грузия",
    "AM": "Армения",
    "AZ": "Азербайджан",
    "MN": "Монголия",
    "TH": "Таиланд",
    "MY": "Малайзия",
    "ID": "Индонезия",
    "VN": "Вьетнам",
    "PH": "Филиппины",
    "HK": "Гонконг",
    "TW": "Тайвань",
    "SA": "Саудовская Аравия",
    "QA": "Катар",
    "ZA": "ЮАР",
    "EG": "Египет",
}


def country_name(code: str) -> str:
    if not code:
        return "Не определена"
    if code in COUNTRY_NAMES:
        return COUNTRY_NAMES[code]
    try:
        from phonenumbers.geocoder import _region_display_name

        return _region_display_name(code, "ru") or code
    except Exception:
        return code


def flag(code: str) -> str:
    """«KG» → 🇰🇬 (regional indicator letters)."""
    if len(code) != 2 or not code.isalpha():
        return "🏳️"
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code.upper())


@cache
def _reader():
    path = settings.GEOIP_PATH
    if not path.exists():
        return None
    try:
        import maxminddb

        return maxminddb.open_database(str(path))
    except Exception:
        logger.exception("GeoIP database %s could not be opened", path)
        return None


def reset_reader():
    _reader.cache_clear()


def country_for_ip(ip: str | None) -> str:
    if not ip:
        return ""
    try:
        if not ipaddress.ip_address(ip).is_global:
            return ""
    except ValueError:
        return ""
    reader = _reader()
    if reader is None:
        return ""
    try:
        record = reader.get(ip) or {}
    except Exception:
        return ""
    return ((record.get("country") or {}).get("iso_code") or "").upper()[:2]
