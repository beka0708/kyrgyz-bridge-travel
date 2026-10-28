import django_filters
from rest_framework.generics import ListAPIView

from apps.content.models import FAQ, GalleryPost, Guide, Partner, Review, Stat

from . import serializers as s


class PublishedListView(ListAPIView):
    """Published items in the order set in the admin; no pagination (short lists)."""

    model = None
    pagination_class = None

    def get_queryset(self):
        return self.model.objects.published()


class GuideListView(PublishedListView):
    model = Guide
    serializer_class = s.GuideSerializer


class ReviewFilter(django_filters.FilterSet):
    tour = django_filters.CharFilter(field_name="tour__slug", help_text="Tour slug")

    class Meta:
        model = Review
        fields = ["tour", "rating"]


class ReviewListView(PublishedListView):
    model = Review
    serializer_class = s.ReviewSerializer
    filterset_class = ReviewFilter

    def get_queryset(self):
        return super().get_queryset().select_related("tour")


class FAQListView(PublishedListView):
    model = FAQ
    serializer_class = s.FAQSerializer


class PartnerListView(PublishedListView):
    model = Partner
    serializer_class = s.PartnerSerializer


class GalleryPostListView(PublishedListView):
    model = GalleryPost
    serializer_class = s.GalleryPostSerializer


class StatListView(PublishedListView):
    model = Stat
    serializer_class = s.StatSerializer
