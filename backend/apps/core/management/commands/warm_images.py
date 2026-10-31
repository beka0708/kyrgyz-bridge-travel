from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import models

from apps.core.images import safe_variants
from apps.core.signals import APPS_WITH_IMAGES


class Command(BaseCommand):
    help = "Build WebP variants for all uploaded images (run after deploy or a media restore)."

    def handle(self, *args, **options):
        count = 0
        for model in apps.get_models():
            fields = [f.name for f in model._meta.get_fields() if isinstance(f, models.ImageField)]
            if not fields or model._meta.app_label not in APPS_WITH_IMAGES:
                continue
            for obj in model.objects.all().iterator():
                for name in fields:
                    fieldfile = getattr(obj, name)
                    if fieldfile:
                        safe_variants(fieldfile)
                        count += 1
        self.stdout.write(self.style.SUCCESS(f"Images processed: {count}"))
