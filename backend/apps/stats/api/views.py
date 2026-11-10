from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.stats.models import ContactChannel
from apps.stats.services import record_click


class ClickSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=ContactChannel.choices)


class ContactClickView(APIView):
    """Count a tap on WhatsApp / phone / email (sent by navigator.sendBeacon). No personal data."""

    permission_classes = [AllowAny]
    authentication_classes = []  # a beacon cannot send a CSRF token; nothing here needs a session
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "stats"

    @extend_schema(request=ClickSerializer, responses={204: None})
    def post(self, request):
        serializer = ClickSerializer(data=request.data)
        if serializer.is_valid():
            record_click(request, serializer.validated_data["channel"])
        return Response(status=status.HTTP_204_NO_CONTENT)
