from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "test"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
TURNSTILE_SECRET_KEY = ""
MEDIA_ROOT = BASE_DIR / ".test-media"  # noqa: F405
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Tests must not depend on a built frontend (static/dist is not in git).
DJANGO_VITE = {"default": {**DJANGO_VITE["default"], "dev_mode": True}}  # noqa: F405

IMAGE_WARMUP = False  # no background threads in tests
