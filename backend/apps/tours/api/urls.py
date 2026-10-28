from rest_framework.routers import SimpleRouter

from .views import TourViewSet

router = SimpleRouter()
router.register("tours", TourViewSet, basename="tour")

urlpatterns = router.urls
