from pathlib import Path

import environ
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPO_DIR = BASE_DIR.parent

env = environ.Env()
environ.Env.read_env(REPO_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
# Public origin without a trailing slash; used for links in emails, sitemap, Open Graph.
SITE_URL = env("SITE_URL", default="http://localhost:8000").rstrip("/")

INSTALLED_APPS = [
    # unfold must come before django.contrib.admin
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    # third party
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    # local
    "apps.core",
    "apps.tours",
    "apps.content",
    "apps.inquiries",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "apps.core.middleware.AdminLocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_settings",
            ],
        },
    },
]

DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://kgtours:kgtours@localhost:5434/kgtours"),
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# The public site is English only; the admin is switched to Russian by AdminLocaleMiddleware.
LANGUAGE_CODE = "en"
ADMIN_LANGUAGE_CODE = "ru"
LANGUAGES = [("en", "English"), ("ru", "Русский")]
TIME_ZONE = "Asia/Bishkek"
USE_I18N = True
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = env.path("STATIC_ROOT", default=str(BASE_DIR / "staticfiles"))
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = env.path("MEDIA_ROOT", default=str(BASE_DIR / "media"))
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 30 * 1024 * 1024

# --- Email -------------------------------------------------------------------
EMAIL_CONFIG = env.email_url("EMAIL_URL", default="consolemail://")
vars().update(EMAIL_CONFIG)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Kyrgyz Tours <noreply@localhost>")
# Fallback recipient when SiteSettings.inquiry_email is empty.
INQUIRY_NOTIFY_EMAIL = env("INQUIRY_NOTIFY_EMAIL", default="")

# --- Anti-spam -----------------------------------------------------------------
# Cloudflare Turnstile; verification is skipped when the secret is empty (dev, tests).
TURNSTILE_SECRET_KEY = env("TURNSTILE_SECRET_KEY", default="")
TURNSTILE_SITE_KEY = env("TURNSTILE_SITE_KEY", default="")

# --- DRF / OpenAPI -------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_RATES": {"inquiries": env("INQUIRY_THROTTLE_RATE", default="5/hour")},
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Kyrgyz Tours API",
    "DESCRIPTION": "Public read API for tours and site content, plus the inquiry form.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    # Group endpoints in Swagger by resource (tours, faq, inquiries…) instead of one "v1" tag.
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "ENUM_NAME_OVERRIDES": {
        "TourTypeEnum": "apps.tours.models.TourType",
        "InquiryStatusEnum": "apps.inquiries.models.InquiryStatus",
    },
}

# --- Admin (django-unfold) -----------------------------------------------------
UNFOLD = {
    "SITE_TITLE": "Kyrgyz Tours",
    "SITE_HEADER": "Kyrgyz Tours",
    "SITE_SUBHEADER": "Управление сайтом",
    "SITE_SYMBOL": "landscape",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "COLORS": {
        "primary": {
            "50": "oklch(98% .016 73.684)",
            "100": "oklch(95.4% .038 75.164)",
            "200": "oklch(90.1% .076 70.697)",
            "300": "oklch(83.7% .128 66.29)",
            "400": "oklch(75% .183 55.934)",
            "500": "oklch(70.5% .213 47.604)",
            "600": "oklch(64.6% .222 41.116)",
            "700": "oklch(55.3% .195 38.402)",
            "800": "oklch(47% .157 37.304)",
            "900": "oklch(40.8% .123 38.172)",
            "950": "oklch(26.6% .079 36.259)",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Заявки",
                "items": [
                    {
                        "title": "Заявки с сайта",
                        "icon": "mail",
                        "link": reverse_lazy("admin:inquiries_inquiry_changelist"),
                        "badge": "apps.inquiries.admin.new_inquiries_badge",
                    },
                ],
            },
            {
                "title": "Туры",
                "items": [
                    {
                        "title": "Туры",
                        "icon": "hiking",
                        "link": reverse_lazy("admin:tours_tour_changelist"),
                    },
                    {
                        "title": "Дни маршрутов",
                        "icon": "route",
                        "link": reverse_lazy("admin:tours_tourday_changelist"),
                    },
                ],
            },
            {
                "title": "Контент",
                "items": [
                    {
                        "title": "Гиды",
                        "icon": "badge",
                        "link": reverse_lazy("admin:content_guide_changelist"),
                    },
                    {
                        "title": "Отзывы",
                        "icon": "reviews",
                        "link": reverse_lazy("admin:content_review_changelist"),
                    },
                    {
                        "title": "Частые вопросы",
                        "icon": "help",
                        "link": reverse_lazy("admin:content_faq_changelist"),
                    },
                    {
                        "title": "Партнёры",
                        "icon": "handshake",
                        "link": reverse_lazy("admin:content_partner_changelist"),
                    },
                    {
                        "title": "Живые кадры",
                        "icon": "photo_library",
                        "link": reverse_lazy("admin:content_gallerypost_changelist"),
                    },
                    {
                        "title": "Счётчики",
                        "icon": "pin",
                        "link": reverse_lazy("admin:content_stat_changelist"),
                    },
                ],
            },
            {
                "title": "Настройки",
                "items": [
                    {
                        "title": "Контакты и SEO",
                        "icon": "settings",
                        "link": reverse_lazy("admin:core_sitesettings_changelist"),
                    },
                    {
                        "title": "Пользователи",
                        "icon": "person",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
        ],
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
