from django.urls import path

from . import views

urlpatterns = [
    path("guides/", views.GuideListView.as_view(), name="guides"),
    path("reviews/", views.ReviewListView.as_view(), name="reviews"),
    path("faq/", views.FAQListView.as_view(), name="faq"),
    path("partners/", views.PartnerListView.as_view(), name="partners"),
    path("gallery/", views.GalleryPostListView.as_view(), name="gallery"),
    path("stats/", views.StatListView.as_view(), name="stats"),
]
