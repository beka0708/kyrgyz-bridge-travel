import logging

from django.conf import settings
from django.urls import reverse

from apps.inquiries.services import _email, notification_recipients

from .models import Review

logger = logging.getLogger(__name__)


def notify_about_review(review: Review) -> bool:
    """Email the agency about a guest review waiting for moderation (best effort)."""
    recipients = notification_recipients()
    if not recipients:
        return False
    context = {
        "review": review,
        "stars": "★" * review.rating + "☆" * (5 - review.rating),
        "admin_url": settings.SITE_URL + reverse("admin:content_review_change", args=[review.pk]),
    }
    tour = review.tour.title if review.tour else "без тура"
    message = _email(
        f"Новый отзыв {review.rating}★: {review.author_name} — {tour}",
        "new_review",
        context,
        to=recipients,
        reply_to=[review.email] if review.email else None,
    )
    try:
        message.send()
    except Exception:
        logger.exception("Failed to send notification for review %s", review.pk)
        return False
    return True
