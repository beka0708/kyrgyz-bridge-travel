from django.urls import path

from . import views

app_name = "tours"

urlpatterns = [
    path("", views.tour_list, name="list"),
    path("<slug:slug>/", views.tour_detail, name="detail"),
]
