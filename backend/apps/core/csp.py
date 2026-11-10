"""Content-Security-Policy for the public site.

The browser runs scripts only from our own domain and the few services we use (maps, Google
Analytics, Cloudflare Turnstile); an injected <script> or a link to a foreign script is refused.
Our two small inline scripts carry a per-request nonce. Alpine needs 'unsafe-eval' for its
attribute expressions (x-data, @click) — those come from our own templates only.

The admin and the API docs are excluded: they are behind a login and use their own inline code.
"""

import secrets
from urllib.parse import urlsplit

from django.conf import settings


def _origin(url: str) -> str:
    parts = urlsplit(
        url.replace("{s}", "a").replace("{z}", "0").replace("{x}", "0").replace("{y}", "0")
    )
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else ""


def _map_origins() -> list[str]:
    cfg = settings.MAP
    urls = [cfg["STYLE_URL"], cfg["TERRAIN_TILES"], *cfg["TOPO_TILES"]]
    origins = {_origin(u) for u in urls}
    # OpenTopoMap rotates a/b/c subdomains: one wildcard instead of three entries
    wild = {
        o.split("://")[0] + "://*." + o.split("://")[1].split(".", 1)[1]
        for o in origins
        if "://a." in o
    }
    covered = {
        o
        for o in origins
        if any(o.split("://")[1].split(".", 1)[-1] == w.split("*.")[1] for w in wild)
    }
    return sorted((origins - covered) | wild - {""})


GOOGLE = [
    "https://www.googletagmanager.com",
    "https://*.google-analytics.com",
    "https://*.analytics.google.com",
]
TURNSTILE = "https://challenges.cloudflare.com"


def build_policy(nonce: str) -> str:
    maps = _map_origins()
    dev = []
    if settings.DJANGO_VITE["default"]["dev_mode"]:
        port = settings.DJANGO_VITE["default"]["dev_server_port"]
        dev = [f"http://localhost:{port}", f"ws://localhost:{port}"]
    directives = {
        "default-src": ["'self'"],
        "script-src": ["'self'", f"'nonce-{nonce}'", "'unsafe-eval'", GOOGLE[0], TURNSTILE, *dev],
        # inline style attributes (view-transition names, CSS variables) and Alpine's style toggles
        "style-src": ["'self'", "'unsafe-inline'", *dev],
        "img-src": ["'self'", "data:", "blob:", *maps, *GOOGLE, *dev],
        "font-src": ["'self'", "data:", *dev],
        "connect-src": ["'self'", *maps, *GOOGLE, TURNSTILE, *dev],
        "worker-src": ["'self'", "blob:"],
        "frame-src": [TURNSTILE],
        "frame-ancestors": ["'none'"],
        "form-action": ["'self'"],
        "base-uri": ["'self'"],
        "object-src": ["'none'"],
    }
    policy = "; ".join(f"{name} {' '.join(values)}" for name, values in directives.items())
    if not settings.DEBUG:
        policy += "; upgrade-insecure-requests"
    return policy


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.skip = (f"/{settings.ADMIN_URL}", "/api/docs/", "/api/redoc/", "/api/schema/")
        self.header = (
            "Content-Security-Policy-Report-Only"
            if settings.CSP_REPORT_ONLY
            else "Content-Security-Policy"
        )

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(16)
        response = self.get_response(request)
        is_page = "text/html" in response.get("Content-Type", "")
        if settings.CSP_ENABLED and is_page and not request.path.startswith(self.skip):
            response.headers.setdefault(self.header, build_policy(request.csp_nonce))
        return response
