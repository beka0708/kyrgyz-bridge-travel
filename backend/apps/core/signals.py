from django.db import models, transaction
from django.db.models.signals import post_save

from .images import warm

APPS_WITH_IMAGES = {"core", "tours", "content"}


def _image_fields(model):
    return [f.name for f in model._meta.get_fields() if isinstance(f, models.ImageField)]


def warm_images_on_save(sender, instance, **kwargs):
    files = [getattr(instance, name) for name in _image_fields(sender)]
    transaction.on_commit(lambda: warm(files))


def connect():
    """Build WebP variants in the background whenever an object with photos is saved."""
    from django.apps import apps

    for model in apps.get_models():
        if model._meta.app_label in APPS_WITH_IMAGES and _image_fields(model):
            post_save.connect(
                warm_images_on_save, sender=model, dispatch_uid=f"warm-{model._meta.label}"
            )
