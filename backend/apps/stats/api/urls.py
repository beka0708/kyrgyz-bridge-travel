from django.urls import path

from .views import ContactClickView

urlpatterns = [
    path("stats/click/", ContactClickView.as_view(), name="stats-click"),
]
