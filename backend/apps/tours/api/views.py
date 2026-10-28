from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.tours.geo import bounds
from apps.tours.models import Tour, TourDay

from .serializers import TourDetailSerializer, TourListSerializer, TourRouteSerializer


class TourViewSet(ReadOnlyModelViewSet):
    """Published tours. Filter: `?tour_type=solo|group`, `?is_featured=true`, `?difficulty=`."""

    lookup_field = "slug"
    filterset_fields = ["tour_type", "is_featured", "difficulty"]
    pagination_class = None  # the catalogue is small (tens of tours)

    def get_queryset(self):
        qs = Tour.objects.published()
        if self.action == "retrieve":
            qs = qs.prefetch_related(
                "images",
                "list_items",
                Prefetch("days", queryset=TourDay.objects.prefetch_related("images")),
            )
        return qs

    def get_serializer_class(self):
        return TourDetailSerializer if self.action == "retrieve" else TourListSerializer

    @extend_schema(responses=TourRouteSerializer)
    @action(detail=True)
    def route(self, request, slug=None):
        """Route geometry by day for the map."""
        tour = self.get_object()
        days = list(tour.days.all())
        data = {"slug": tour.slug, "days": days, "bounds": bounds(days)}
        return Response(TourRouteSerializer(data).data)
