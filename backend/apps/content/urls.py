from django.urls import path

from . import views

app_name = "content"

urlpatterns = [
    path("new/", views.review_submit, name="review_submit"),
]
