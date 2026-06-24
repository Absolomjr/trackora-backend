from rest_framework import serializers

from .models import Category, Product, Supplier


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(source='products.count', read_only=True)

    class Meta:
        model = Category
        fields = (
            'id', 'name', 'slug', 'description', 'is_active',
            'product_count', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'slug', 'created_at', 'updated_at')


class SupplierSerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(source='products.count', read_only=True)

    class Meta:
        model = Supplier
        fields = (
            'id', 'name', 'contact_person', 'email', 'phone', 'address',
            'is_active', 'product_count', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class ProductSerializer(serializers.ModelSerializer):
    # Human-readable nested labels for the React UI
    category_name = serializers.CharField(source='category.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True, default=None)
    unit_display = serializers.CharField(source='get_unit_display', read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    stock_value = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'sku', 'category', 'category_name',
            'supplier', 'supplier_name', 'description', 'unit', 'unit_display',
            'cost_price', 'selling_price', 'quantity', 'reorder_level',
            'image', 'is_active', 'is_low_stock', 'stock_value',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'quantity', 'created_at', 'updated_at')

    def validate(self, attrs):
        cost = attrs.get('cost_price', getattr(self.instance, 'cost_price', None))
        selling = attrs.get('selling_price', getattr(self.instance, 'selling_price', None))
        if cost is not None and selling is not None and selling < cost:
            raise serializers.ValidationError(
                {'selling_price': 'Selling price should not be lower than cost price.'}
            )
        return attrs
