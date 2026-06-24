import django_filters

from .models import Product


class ProductFilter(django_filters.FilterSet):
    """Filtering for the products list endpoint."""

    category = django_filters.NumberFilter(field_name='category_id')
    supplier = django_filters.NumberFilter(field_name='supplier_id')
    min_price = django_filters.NumberFilter(field_name='selling_price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='selling_price', lookup_expr='lte')
    low_stock = django_filters.BooleanFilter(method='filter_low_stock')

    class Meta:
        model = Product
        fields = ['category', 'supplier', 'unit', 'is_active']

    def filter_low_stock(self, queryset, name, value):
        from django.db.models import F
        if value:
            return queryset.filter(quantity__lte=F('reorder_level'))
        return queryset.filter(quantity__gt=F('reorder_level'))
