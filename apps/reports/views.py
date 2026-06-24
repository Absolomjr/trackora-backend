from datetime import timedelta
from decimal import Decimal

from django.db.models import (
    Count, DecimalField, ExpressionWrapper, F, Sum, Value,
)
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsManager
from apps.inventory.models import Product, Supplier
from apps.sales.models import Order, OrderItem

DEC = DecimalField(max_digits=18, decimal_places=2)
ZERO = Value(Decimal('0'), output_field=DEC)


def _completed_items():
    return OrderItem.objects.filter(order__status=Order.Status.COMPLETED)


def _line_revenue():
    return ExpressionWrapper(F('quantity') * F('unit_price'), output_field=DEC)


def _line_profit():
    return ExpressionWrapper(
        F('quantity') * (F('unit_price') - F('unit_cost')), output_field=DEC
    )


class DashboardView(APIView):
    """High-level KPIs for the React dashboard."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        month_start = today.replace(day=1)

        completed = Order.objects.filter(status=Order.Status.COMPLETED)
        items = _completed_items()

        low_stock_count = Product.objects.filter(
            is_active=True, quantity__lte=F('reorder_level')
        ).count()

        today_sales = items.filter(order__created_at__date=today).aggregate(
            v=Coalesce(Sum(_line_revenue()), ZERO)
        )['v']
        month_sales = items.filter(order__created_at__date__gte=month_start).aggregate(
            v=Coalesce(Sum(_line_revenue()), ZERO)
        )['v']

        top_selling = list(
            items.values('product', 'product__name', 'product__sku')
            .annotate(
                quantity_sold=Sum('quantity'),
                revenue=Coalesce(Sum(_line_revenue()), ZERO),
            )
            .order_by('-quantity_sold')[:5]
        )

        return Response({
            'total_products': Product.objects.filter(is_active=True).count(),
            'total_suppliers': Supplier.objects.filter(is_active=True).count(),
            'total_customers': Order.objects.exclude(customer__isnull=True)
                .values('customer').distinct().count(),
            'low_stock_items': low_stock_count,
            'total_orders': completed.count(),
            'today_sales': today_sales,
            'monthly_sales': month_sales,
            'inventory_cost_value': Product.objects.aggregate(
                v=Coalesce(Sum(F('quantity') * F('cost_price'), output_field=DEC), ZERO)
            )['v'],
            'top_selling_products': top_selling,
        })


class LowStockReportView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        products = Product.objects.filter(
            is_active=True, quantity__lte=F('reorder_level')
        ).select_related('category').order_by('quantity')
        data = [{
            'id': p.id,
            'name': p.name,
            'sku': p.sku,
            'category': p.category.name,
            'quantity': p.quantity,
            'reorder_level': p.reorder_level,
            'shortfall': max(p.reorder_level - p.quantity, 0),
        } for p in products]
        return Response({'count': len(data), 'results': data})


class DailySalesReportView(APIView):
    """Sales totals grouped by day. ?days=30 (default)."""
    permission_classes = [IsManager]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        start = timezone.now().date() - timedelta(days=days - 1)
        rows = (
            _completed_items()
            .filter(order__created_at__date__gte=start)
            .annotate(day=TruncDate('order__created_at'))
            .values('day')
            .annotate(
                orders=Count('order', distinct=True),
                revenue=Coalesce(Sum(_line_revenue()), ZERO),
                profit=Coalesce(Sum(_line_profit()), ZERO),
            )
            .order_by('day')
        )
        return Response(list(rows))


class MonthlySalesReportView(APIView):
    """Sales totals grouped by month. ?months=12 (default)."""
    permission_classes = [IsManager]

    def get(self, request):
        months = int(request.query_params.get('months', 12))
        start = (timezone.now().date().replace(day=1)
                 - timedelta(days=31 * (months - 1))).replace(day=1)
        rows = (
            _completed_items()
            .filter(order__created_at__date__gte=start)
            .annotate(month=TruncMonth('order__created_at'))
            .values('month')
            .annotate(
                orders=Count('order', distinct=True),
                revenue=Coalesce(Sum(_line_revenue()), ZERO),
                profit=Coalesce(Sum(_line_profit()), ZERO),
            )
            .order_by('month')
        )
        return Response(list(rows))


class ProfitReportView(APIView):
    """Revenue, cost and profit over a window. ?days=30 (default)."""
    permission_classes = [IsManager]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        start = timezone.now().date() - timedelta(days=days - 1)
        items = _completed_items().filter(order__created_at__date__gte=start)

        agg = items.aggregate(
            revenue=Coalesce(Sum(_line_revenue()), ZERO),
            cost=Coalesce(Sum(F('quantity') * F('unit_cost'), output_field=DEC), ZERO),
            profit=Coalesce(Sum(_line_profit()), ZERO),
            units_sold=Coalesce(Sum('quantity'), Value(0)),
        )
        margin = (agg['profit'] / agg['revenue'] * 100) if agg['revenue'] else Decimal('0')
        agg['profit_margin_pct'] = round(margin, 2)
        agg['period_days'] = days
        return Response(agg)


class BestSellingReportView(APIView):
    """Top products by units sold. ?limit=10 (default)."""
    permission_classes = [IsManager]

    def get(self, request):
        limit = int(request.query_params.get('limit', 10))
        rows = (
            _completed_items()
            .values('product', 'product__name', 'product__sku')
            .annotate(
                quantity_sold=Sum('quantity'),
                revenue=Coalesce(Sum(_line_revenue()), ZERO),
                profit=Coalesce(Sum(_line_profit()), ZERO),
            )
            .order_by('-quantity_sold')[:limit]
        )
        return Response(list(rows))
