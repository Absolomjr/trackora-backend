from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from apps.accounts.permissions import IsAdmin

from .models import Lead
from .serializers import LeadCreateSerializer, LeadSerializer


class LeadRateThrottle(AnonRateThrottle):
    """Dedicated bucket so marketing-form abuse can't exhaust other anon limits."""

    scope = 'lead'


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class LeadCreateView(generics.CreateAPIView):
    """POST /api/leads/ — public. Captures a signup or demo request."""

    serializer_class = LeadCreateSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LeadRateThrottle]

    def perform_create(self, serializer):
        serializer.save(
            ip_address=_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')[:300],
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # Don't echo the stored record back to an anonymous caller.
        return Response(
            {'detail': "Thanks! We've received your request and will be in touch shortly."},
            status=status.HTTP_201_CREATED,
        )


class LeadListView(generics.ListAPIView):
    """GET /api/leads/all/ — admin only."""

    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ('kind', 'status')
    search_fields = ('full_name', 'email', 'phone', 'business_name')
    ordering_fields = ('created_at', 'status')


class LeadDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/leads/all/<pk>/ — admin only.

    Only `status` and `note` are writable; see LeadSerializer.read_only_fields.
    """

    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    permission_classes = [IsAdmin]
