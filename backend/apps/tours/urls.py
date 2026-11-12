from django.urls import path

from . import views

app_name = "tours"

urlpatterns = [
    path("", views.tour_list, name="list"),
    path("dates/", views.departures_calendar, name="dates"),
    path("<slug:slug>/", views.tour_detail, name="detail"),
]
