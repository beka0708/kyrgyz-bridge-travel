import json
import logging
import re
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMessage
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


def rate_limited(ip: str | None, limit: int = 5, window: int = 3600) -> bool:
    """Per-IP limit for the no-JS form; the API has DRF throttling with the same rate."""
    if not ip:
        return False
    key = f"inquiry-rate:{ip}"
    count = cache.get(key, 0)
    if count >= limit:
        return True
    cache.set(key, count + 1, window)
    return False


def create_inquiry(*, data: dict, request, is_spam: bool = False) -> Inquiry:
    inquiry = Inquiry(
        **data,
        status=InquiryStatus.SPAM if is_spam else InquiryStatus.NEW,
        ip=client_ip(request),
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


def notify_about_inquiry(inquiry: Inquiry) -> bool:
    """Email the agency. Failures are logged and retried by `manage.py resend_inquiries`."""
    recipients = notification_recipients()
    if not recipients:
        logger.warning(
            "No inquiry email configured; inquiry %s saved without notification", inquiry.pk
        )
        return False

    context = {
        "inquiry": inquiry,
        "admin_url": settings.SITE_URL
        + reverse("admin:inquiries_inquiry_change", args=[inquiry.pk]),
        "whatsapp_link": whatsapp_link(inquiry.contact),
    }
    tour = inquiry.tour_title or "консультация"
    message = EmailMessage(
        subject=f"Новая заявка: {inquiry.name} — {tour}, {inquiry.people} чел.",
        body=render_to_string("emails/new_inquiry.txt", context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
        reply_to=[inquiry.email],  # «Reply» in the mail app goes straight to the traveller
    )
    try:
        message.send()
    except Exception:
        logger.exception("Failed to send notification for inquiry %s", inquiry.pk)
        return False

    Inquiry.objects.filter(pk=inquiry.pk).update(notified_at=timezone.now())
    inquiry.notified_at = timezone.now()
    return True
