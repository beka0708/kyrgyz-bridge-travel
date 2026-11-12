"""Counts visitors by country on public HTML pages (not the admin, the API or files)."""

from .services import record_visit

PUBLIC_APPS = {"core", "tours", "content"}


class VisitCounterMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        match = getattr(request, "resolver_match", None)
        if (
            request.method == "GET"
            and response.status_code == 200
            and match is not None
            and match.app_name in PUBLIC_APPS
            and response.get("Content-Type", "").startswith("text/html")
        ):
            try:
                record_visit(request)
            except Exception:  # statistics must never break a page
                import logging

                logging.getLogger(__name__).exception("visit counter failed")
        return response
