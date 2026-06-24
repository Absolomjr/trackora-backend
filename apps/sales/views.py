from django.db import transaction
from django.db.models import F
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsManagerOrReadOnly, IsStaffOrAbove
from apps.inventory.models import Product

from .models import Customer, Order
from .serializers import CustomerSerializer, OrderSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsStaffOrAbove]
    search_fields = ['name', 'phone', 'email']
    ordering_fields = ['name', 'created_at']


class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Sales orders. Creating one snapshots prices and deducts stock.
    Orders are not edited; use the `cancel` action to void one and restore stock.
    """
    queryset = Order.objects.select_related('customer', 'created_by').prefetch_related('items__product')
    serializer_class = OrderSerializer
    permission_classes = [IsStaffOrAbove]
    search_fields = ['reference', 'customer__name', 'note']
    ordering_fields = ['created_at', 'reference']
    filterset_fields = ['status', 'payment_method', 'customer']

    @action(detail=True, methods=['post'], permission_classes=[IsManagerOrReadOnly])
    def cancel(self, request, pk=None):
        """Void a completed order and return its items to stock (Manager/Admin)."""
        order = self.get_object()
        if order.status == Order.Status.CANCELLED:
            return Response(
                {'detail': 'Order is already cancelled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            for item in order.items.select_related('product'):
                Product.objects.filter(pk=item.product_id).update(
                    quantity=F('quantity') + item.quantity
                )
            order.status = Order.Status.CANCELLED
            order.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(order).data)
