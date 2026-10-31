from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    verbose_name = "Сайт"

    def ready(self):
        from .signals import connect

        connect()
