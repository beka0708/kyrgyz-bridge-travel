from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

v1 = [
    path("", include("apps.core.api.urls")),
    path("", include("apps.tours.api.urls")),
    path("", include("apps.content.api.urls")),
    path("", include("apps.inquiries.api.urls")),
]

urlpatterns = [
    path("v1/", include((v1, "api"), namespace="v1")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
