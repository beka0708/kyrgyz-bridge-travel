from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.models import SiteSettings
from apps.core.seo import PageMeta, absolute
from apps.inquiries.services import client_ip, rate_limited, verify_turnstile
from apps.tours.models import Tour

from .forms import ReviewSubmitForm
from .models import REVIEW_HIGHLIGHTS
from .services import notify_about_review


def review_submit(request):
    """«Share your experience»: a guest review, hidden until the agency publishes it."""
    tour_slug = request.GET.get("tour", "")
    if request.method == "POST":
        form = ReviewSubmitForm(request.POST)
        if request.POST.get("website"):  # honeypot: pretend it worked
            return redirect(f"{reverse('content:review_submit')}?sent=1")
        if not verify_turnstile(request.POST.get("cf-turnstile-response", ""), client_ip(request)):
            form.add_error(None, "Please confirm you are not a robot and send again.")
        elif rate_limited(client_ip(request), limit=3, scope="review"):
            form.add_error(None, "Too many reviews from your network today. Please try later.")
        elif form.is_valid():
            review = form.save()
            transaction.on_commit(lambda: notify_about_review(review))
            return redirect(f"{reverse('content:review_submit')}?sent=1&r={review.rating}")
    else:
        form = ReviewSubmitForm(initial={"tour": tour_slug})
    meta = PageMeta(
        title="Share your experience",
        description="Travelled with us? Tell other travellers how it was.",
        canonical=absolute(reverse("content:review_submit")),
    )
    tours = list(Tour.objects.published().only("title", "slug", "cover"))
    selected = request.POST.get("tour") or tour_slug
    tour = next((t for t in tours if t.slug == selected), None)
    site = SiteSettings.load()
    return render(
        request,
        "pages/review_form.html",
        {
            "form": form,
            "tours": tours,
            "tour": tour,
            "photo": tour.cover if tour else site.hero_image,
            "highlights": REVIEW_HIGHLIGHTS,
            "chosen": request.POST.getlist("highlights"),
            "sent": request.GET.get("sent") == "1",
            "sent_rating": int(request.GET["r"]) if request.GET.get("r", "").isdigit() else 0,
            "selected_tour": selected,
            "meta": meta,
            "robots_noindex": True,
        },
    )
