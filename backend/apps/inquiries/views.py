from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import InquiryForm
from .services import client_ip, create_inquiry, rate_limited, verify_turnstile


def _safe_next(request):
    url = request.POST.get("next") or "/"
    if not url_has_allowed_host_and_scheme(url, {request.get_host()}, request.is_secure()):
        url = "/"
    return url.split("#")[0].split("?")[0]


@require_POST
def submit_inquiry(request):
    """Fallback for browsers without JavaScript; the page normally posts to the API."""
    form = InquiryForm(request.POST)
    ip = client_ip(request)
    error = None
    if rate_limited(ip):
        error = "Too many requests from your network. Please message us on WhatsApp instead."
    elif not verify_turnstile(request.POST.get("cf-turnstile-response", ""), ip):
        error = "Please confirm you are not a robot and send the form again."
    elif form.is_valid():
        data = dict(form.cleaned_data)
        honeypot = data.pop("website", "")
        create_inquiry(data=data, request=request, is_spam=bool(honeypot))
        return redirect(f"{_safe_next(request)}?sent=1#contact")
    return render(request, "pages/inquiry_error.html", {"form": form, "error": error}, status=400)
