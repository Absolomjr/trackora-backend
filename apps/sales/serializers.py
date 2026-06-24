from django.db import transaction
from django.db.models import F
from rest_framework import serializers

from apps.inventory.models import Product
from apps.stock.utils import generate_reference

from .models import Customer, Order, OrderItem


class CustomerSerializer(serializers.ModelSerializer):
    order_count = serializers.IntegerField(source='orders.count', read_only=True)

    class Meta:
        model = Customer
        fields = (
            'id', 'name', 'phone', 'email', 'address',
            'order_count', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class OrderItemWriteSerializer(serializers.Serializer):
    """Input for an order line — only product + quantity; prices are snapshotted server-side."""
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    sku = serializers.CharField(source='product.sku', read_only=True)
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            'id', 'product', 'product_name', 'sku',
            'quantity', 'unit_price', 'unit_cost', 'subtotal',
        )


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    # Write-only nested input for creating an order.
    line_items = OrderItemWriteSerializer(many=True, write_only=True)

    customer_name = serializers.CharField(source='customer.name', read_only=True, default=None)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)

    subtotal = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    profit = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'reference', 'customer', 'customer_name',
            'status', 'status_display', 'payment_method', 'payment_method_display',
            'discount', 'note', 'line_items', 'items',
            'subtotal', 'total', 'profit',
            'created_by', 'created_by_name', 'created_at',
        )
        read_only_fields = ('id', 'reference', 'status', 'created_by', 'created_at')

    def validate_line_items(self, value):
        if not value:
            raise serializers.ValidationError('An order needs at least one line item.')
        return value

    @transaction.atomic
    def create(self, validated_data):
        line_items = validated_data.pop('line_items')
        validated_data['created_by'] = self.context['request'].user
        validated_data['reference'] = generate_reference('ORD', Order)
        order = Order.objects.create(**validated_data)

        for line in line_items:
            product = line['product']
            qty = line['quantity']
            locked = Product.objects.select_for_update().get(pk=product.pk)
            if locked.quantity < qty:
                raise serializers.ValidationError(
                    {'line_items': f'Not enough stock for "{locked.name}". '
                                   f'Available: {locked.quantity}, requested: {qty}.'}
                )
            OrderItem.objects.create(
                order=order,
                product=locked,
                quantity=qty,
                unit_price=locked.selling_price,
                unit_cost=locked.cost_price,
            )
            # Completed sale -> deduct stock.
            Product.objects.filter(pk=locked.pk).update(quantity=F('quantity') - qty)

        return order
