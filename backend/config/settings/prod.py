from .base import *  # noqa: F403
from .base import env

DEBUG = False
SECRET_KEY = env("SECRET_KEY")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
# The container health check calls http://127.0.0.1:8000/healthz/ from inside the container.
# Outside traffic only reaches Django through Caddy, which serves just the real domain.
ALLOWED_HOSTS = [*ALLOWED_HOSTS, "127.0.0.1"]  # noqa: F405
SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
# Turn on once it is known that every subdomain of the client's domain has HTTPS.
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # admin login lasts a week

# Shared between gunicorn workers so throttling works across processes.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": env("CACHE_DIR", default="/tmp/django-cache"),
    }
}

# WhiteNoise serves /static/ with compression and long caching (prod only: in dev runserver does).
MIDDLEWARE = [
    *MIDDLEWARE[:1],  # noqa: F405 - SecurityMiddleware first
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],  # noqa: F405
]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Pre-compressed (gzip/brotli) files; no extra hashing: Vite already hashes its file names.
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}


def _immutable(path, url):
    """Vite bundles carry a content hash in the name, so browsers may cache them for a year."""
    return url.startswith("/static/dist/assets/")


WHITENOISE_IMMUTABLE_FILE_TEST = _immutable

# Error reports: only when SENTRY_DSN is set (free plan is enough for this site).
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        send_default_pii=False,  # no visitor emails or IPs in error reports
        traces_sample_rate=0.0,
        environment=env("SENTRY_ENVIRONMENT", default="production"),
    )
