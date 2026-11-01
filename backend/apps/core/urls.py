from django.urls import path

from . import views, views_classic

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("privacy/", views.privacy, name="privacy"),
    path("classic/", views_classic.home_classic, name="home_classic"),
]
