from django.urls import path
from rest_framework.routers import SimpleRouter

from .admin_views import RouteBuildView, RouteGpxView
from .views import TourViewSet

router = SimpleRouter()
router.register("tours", TourViewSet, basename="tour")

urlpatterns = [
    *router.urls,
    path("admin/routes/build/", RouteBuildView.as_view(), name="route-build"),
    path("admin/routes/gpx/", RouteGpxView.as_view(), name="route-gpx"),
]
