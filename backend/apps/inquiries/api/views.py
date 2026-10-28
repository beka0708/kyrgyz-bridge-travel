from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.inquiries.services import client_ip, create_inquiry, verify_turnstile

from .serializers import InquiryCreateSerializer, InquiryResponseSerializer


class InquiryCreateView(GenericAPIView):
    """Booking / question form. Rate-limited per IP; protected by a honeypot and Turnstile."""

    serializer_class = InquiryCreateSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "inquiries"

    @extend_schema(responses={201: InquiryResponseSerializer})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        honeypot = data.pop("website", "")
        token = data.pop("turnstile_token", "")

        if not verify_turnstile(token, client_ip(request)):
            raise ValidationError({"turnstile_token": "Verification failed, please retry."})

        # Bots get the same answer as people, so they cannot learn about the honeypot.
        create_inquiry(data=data, request=request, is_spam=bool(honeypot))
        return Response({"status": "received"}, status=status.HTTP_201_CREATED)
