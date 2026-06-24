from rest_framework import mixins, viewsets

from apps.accounts.permissions import IsStaffOrAbove

from .models import StockIn, StockOut
from .serializers import StockInSerializer, StockOutSerializer


class StockInViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Stock receipts. Creating one increases product quantities.

    Movements are immutable (no update/delete) to preserve an audit trail —
    correct mistakes with a balancing Stock Out / Stock In instead.
    """
    queryset = StockIn.objects.select_related('supplier', 'created_by').prefetch_related('items__product')
    serializer_class = StockInSerializer
    permission_classes = [IsStaffOrAbove]
    search_fields = ['reference', 'note', 'supplier__name']
    ordering_fields = ['created_at', 'reference']
    filterset_fields = ['supplier']


class StockOutViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Non-sale stock removals. Creating one decreases product quantities."""
    queryset = StockOut.objects.select_related('created_by').prefetch_related('items__product')
    serializer_class = StockOutSerializer
    permission_classes = [IsStaffOrAbove]
    search_fields = ['reference', 'note']
    ordering_fields = ['created_at', 'reference']
    filterset_fields = ['reason']
