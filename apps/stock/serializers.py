from django.db import transaction
from django.db.models import F
from rest_framework import serializers

from apps.inventory.models import Product

from .models import StockIn, StockInItem, StockOut, StockOutItem
from .utils import generate_reference


# ----------------------------------------------------------------------------
# Stock In
# ----------------------------------------------------------------------------
class StockInItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = StockInItem
        fields = ('id', 'product', 'product_name', 'quantity', 'unit_cost', 'subtotal')


class StockInSerializer(serializers.ModelSerializer):
    items = StockInItemSerializer(many=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True, default=None)
    total_cost = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)

    class Meta:
        model = StockIn
        fields = (
            'id', 'reference', 'supplier', 'supplier_name', 'note',
            'items', 'total_cost', 'created_by', 'created_by_name', 'created_at',
        )
        read_only_fields = ('id', 'created_by', 'created_at')
        extra_kwargs = {'reference': {'required': False}}

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError('At least one item is required.')
        return items

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        validated_data['created_by'] = self.context['request'].user
        if not validated_data.get('reference'):
            validated_data['reference'] = generate_reference('SIN', StockIn)
        stock_in = StockIn.objects.create(**validated_data)

        for item in items_data:
            product = item['product']
            qty = item['quantity']
            StockInItem.objects.create(stock_in=stock_in, **item)
            # Increase quantity atomically and refresh the cost price.
            Product.objects.filter(pk=product.pk).update(quantity=F('quantity') + qty)
            if item.get('unit_cost') is not None:
                Product.objects.filter(pk=product.pk).update(cost_price=item['unit_cost'])

        return stock_in


# ----------------------------------------------------------------------------
# Stock Out
# ----------------------------------------------------------------------------
class StockOutItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = StockOutItem
        fields = ('id', 'product', 'product_name', 'quantity')


class StockOutSerializer(serializers.ModelSerializer):
    items = StockOutItemSerializer(many=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)

    class Meta:
        model = StockOut
        fields = (
            'id', 'reference', 'reason', 'reason_display', 'note',
            'items', 'created_by', 'created_by_name', 'created_at',
        )
        read_only_fields = ('id', 'created_by', 'created_at')
        extra_kwargs = {'reference': {'required': False}}

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError('At least one item is required.')
        return items

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        validated_data['created_by'] = self.context['request'].user
        if not validated_data.get('reference'):
            validated_data['reference'] = generate_reference('SOUT', StockOut)
        stock_out = StockOut.objects.create(**validated_data)

        for item in items_data:
            product = item['product']
            qty = item['quantity']
            # Lock the row and verify there is enough stock.
            locked = Product.objects.select_for_update().get(pk=product.pk)
            if locked.quantity < qty:
                raise serializers.ValidationError(
                    {'items': f'Not enough stock for "{locked.name}". '
                              f'Available: {locked.quantity}, requested: {qty}.'}
                )
            StockOutItem.objects.create(stock_out=stock_out, **item)
            Product.objects.filter(pk=product.pk).update(quantity=F('quantity') - qty)

        return stock_out
