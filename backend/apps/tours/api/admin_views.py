"""Staff-only helpers for the route editor in the admin (preview before saving)."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tours.models import TrackSource, validate_waypoints
from apps.tours.services.errors import RoutingError
from apps.tours.services.routing import build_route, gpx_route


class RouteBuildRequestSerializer(serializers.Serializer):
    source = serializers.ChoiceField(choices=TrackSource.choices)
    waypoints = serializers.JSONField(validators=[validate_waypoints])

    def validate_source(self, value):
        if value == TrackSource.GPX:
            raise serializers.ValidationError("Use the GPX endpoint for GPX files.")
        return value


class RouteGpxRequestSerializer(serializers.Serializer):
    file = serializers.FileField()


class RouteResultSerializer(serializers.Serializer):
    track = serializers.JSONField(allow_null=True)
    distance_km = serializers.DecimalField(max_digits=6, decimal_places=1, allow_null=True)
    ascent_m = serializers.IntegerField(allow_null=True)
    waypoints = serializers.JSONField(allow_null=True, required=False)


class RouteErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()


def _respond(build):
    try:
        result = build()
    except RoutingError as exc:
        return Response({"detail": str(exc)}, status=422)
    return Response(RouteResultSerializer(result).data)


class RouteBuildView(APIView):
    """Build a line through the points (straight, by road or by hiking trail)."""

    permission_classes = [IsAdminUser]

    @extend_schema(
        request=RouteBuildRequestSerializer,
        responses={200: RouteResultSerializer, 422: RouteErrorSerializer},
        tags=["admin"],
    )
    def post(self, request):
        data = RouteBuildRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return _respond(lambda: build_route(**data.validated_data))


class RouteGpxView(APIView):
    """Read a GPX file: line, distance, ascent and start/finish points."""

    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser]

    @extend_schema(
        request=RouteGpxRequestSerializer,
        responses={200: RouteResultSerializer, 422: RouteErrorSerializer},
        tags=["admin"],
    )
    def post(self, request):
        data = RouteGpxRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return _respond(lambda: gpx_route(data.validated_data["file"]))
