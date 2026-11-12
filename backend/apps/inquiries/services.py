import json
import logging
import re
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from apps.core.models import SiteSettings

from .models import Inquiry, InquiryStatus

logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def verify_turnstile(token: str, ip: str | None) -> bool:
    """Cloudflare Turnstile check; always passes when no secret is configured (dev, tests)."""
    if not settings.TURNSTILE_SECRET_KEY:
        return True
    if not token:
        return False
    data = urllib.parse.urlencode(
        {"secret": settings.TURNSTILE_SECRET_KEY, "response": token, "remoteip": ip or ""}
    ).encode()
    try:
        with urllib.request.urlopen(TURNSTILE_VERIFY_URL, data=data, timeout=5) as resp:
            return bool(json.load(resp).get("success"))
    except OSError:
        # Do not lose a real lead because Cloudflare is unreachable; honeypot + throttle remain.
        logger.warning("Turnstile verification unavailable, accepting inquiry")
        return True


def client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def rate_limited(
    ip: str | None, limit: int = 5, window: int = 3600, scope: str = "inquiry"
) -> bool:
    """Per-IP limit for plain HTML forms (inquiry, review); the API has DRF throttling."""
    if not ip:
        return False
    key = f"{scope}-rate:{ip}"
    count = cache.get(key, 0)
    if count >= limit:
        return True
    cache.set(key, count + 1, window)
    return False


def inquiry_country(ip: str | None, contact: str) -> str:
    """Where the traveller is: by IP; if unknown, by the phone's country code."""
    from apps.stats.geo import country_for_ip

    country = country_for_ip(ip)
    if country or not contact.startswith("+"):
        return country
    try:
        import phonenumbers

        number = phonenumbers.parse(contact)
        region = phonenumbers.region_code_for_number(number) or (
            phonenumbers.region_code_for_country_code(number.country_code)
        )
        return "" if region in (None, "ZZ", "001") else region
    except phonenumbers.NumberParseException:
        return ""


def create_inquiry(*, data: dict, request, is_spam: bool = False) -> Inquiry:
    ip = client_ip(request)
    inquiry = Inquiry(
        **data,
        status=InquiryStatus.SPAM if is_spam else InquiryStatus.NEW,
        ip=ip,
        country=inquiry_country(ip, data.get("contact", "")),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
    )
    inquiry.save()
    if not is_spam:
        transaction.on_commit(lambda: notify_about_inquiry(inquiry))
    return inquiry


def whatsapp_link(contact: str) -> str:
    """wa.me link when the contact looks like a phone number with a country code."""
    digits = re.sub(r"\D", "", contact or "")
    looks_like_phone = 9 <= len(digits) <= 15 and not re.search(r"[A-Za-z@]", contact or "")
    return f"https://wa.me/{digits}" if looks_like_phone else ""


def notification_recipients() -> list[str]:
    email = SiteSettings.load().inquiry_email or settings.INQUIRY_NOTIFY_EMAIL
    return [email] if email else []


def _when(inquiry: Inquiry) -> str:
    if inquiry.travel_when:
        return inquiry.travel_when
    if inquiry.date_from:
        end = f" – {inquiry.date_to:%d.%m.%Y}" if inquiry.date_to else ""
        return f"{inquiry.date_from:%d.%m.%Y}{end}"
    return ""


def _email(subject, template, context, to, reply_to=None) -> EmailMultiAlternatives:
    """Text + HTML email from templates/emails/<template>.txt / .html."""
    site = SiteSettings.load()
    context = {"site": site, "site_url": settings.SITE_URL, **context}
    message = EmailMultiAlternatives(
        subject=subject,
        body=render_to_string(f"emails/{template}.txt", context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=to,
        reply_to=reply_to,
    )
    message.attach_alternative(render_to_string(f"emails/{template}.html", context), "text/html")
    return message


def notify_about_inquiry(inquiry: Inquiry) -> bool:
    """Email the agency, then thank the traveller (if they left an email).

    Agency failures are logged and retried by `manage.py resend_inquiries`; the traveller's
    confirmation is best effort and never blocks or repeats.
    """
    recipients = notification_recipients()
    if not recipients:
        logger.warning(
            "No inquiry email configured; inquiry %s saved without notification", inquiry.pk
        )
        return False

    rows = [
        ("Имя", inquiry.name),
        ("Email", inquiry.email),
        ("Телефон / WhatsApp", inquiry.contact),
        ("Тур", inquiry.tour_title or "не выбран — нужна консультация"),
        ("Когда", _when(inquiry)),
        ("Человек", inquiry.people),
    ]
    context = {
        "inquiry": inquiry,
        "rows": rows,
        "admin_url": settings.SITE_URL
        + reverse("admin:inquiries_inquiry_change", args=[inquiry.pk]),
        "whatsapp_link": whatsapp_link(inquiry.contact),
    }
    tour = inquiry.tour_title or "консультация"
    message = _email(
        f"Новая заявка: {inquiry.name} — {tour}, {inquiry.people} чел.",
        "new_inquiry",
        context,
        to=recipients,
        # «Reply» in the mail app goes straight to the traveller (when they left an email)
        reply_to=[inquiry.email] if inquiry.email else None,
    )
    try:
        message.send()
    except Exception:
        logger.exception("Failed to send notification for inquiry %s", inquiry.pk)
        return False

    Inquiry.objects.filter(pk=inquiry.pk).update(notified_at=timezone.now())
    inquiry.notified_at = timezone.now()
    send_confirmation(inquiry)
    return True


def send_confirmation(inquiry: Inquiry) -> bool:
    """«We got your request» to the traveller, in English, with a summary and a WhatsApp button."""
    if not inquiry.email:
        return False
    site = SiteSettings.load()
    rows = [
        ("Tour", inquiry.tour_title or "Not sure yet — we'll help you choose"),
        ("When", _when(inquiry)),
        ("Travellers", inquiry.people),
        ("Phone / WhatsApp", inquiry.contact),
    ]
    context = {
        "inquiry": inquiry,
        "rows": rows,
        "whatsapp_url": site.whatsapp_url(
            f"Hi! I sent a request on your website, my name is {inquiry.name}."
        ),
    }
    reply_to = [site.inquiry_email or site.email] if (site.inquiry_email or site.email) else None
    message = _email(
        f"We got your request — {site.brand_name}",
        "inquiry_confirmation",
        context,
        to=[inquiry.email],
        reply_to=reply_to,
    )
    try:
        message.send()
    except Exception:
        logger.exception("Failed to send confirmation for inquiry %s", inquiry.pk)
        return False
    return True
