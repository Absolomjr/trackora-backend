from datetime import timedelta
from decimal import Decimal

from django.conf import settings
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
from apps.sales.models import Customer, Order, OrderItem
from apps.stock.models import StockIn, StockInItem, StockOut, StockOutItem

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


def _pct(cur, prev):
    """Percentage change, tolerant of a zero baseline."""
    cur = Decimal(cur or 0)
    prev = Decimal(prev or 0)
    if prev == 0:
        return round(float(cur > 0) * 100, 1)
    return round(float((cur - prev) / prev * 100), 1)


def _delta(cur, prev):
    pct = _pct(cur, prev)
    return {'pct': abs(pct), 'direction': 'up' if pct >= 0 else 'down'}


class RoleOverviewView(APIView):
    """Role-aware dashboard payload — one call powers the Admin, Manager and
    Staff dashboards, returning only what each role's view needs."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        role = getattr(user, 'role', 'staff')
        today = timezone.now().date()
        d7, p7s, p7e = today - timedelta(days=6), today - timedelta(days=13), today - timedelta(days=7)
        d30, p30s, p30e = today - timedelta(days=29), today - timedelta(days=59), today - timedelta(days=30)
        month_start = today.replace(day=1)
        last_month_end = month_start - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        yesterday = today - timedelta(days=1)

        items = _completed_items()
        completed = Order.objects.filter(status=Order.Status.COMPLETED)

        def revenue(start, end):
            return items.filter(
                order__created_at__date__gte=start, order__created_at__date__lte=end
            ).aggregate(v=Coalesce(Sum(_line_revenue()), ZERO))['v']

        def profit(start, end):
            return items.filter(
                order__created_at__date__gte=start, order__created_at__date__lte=end
            ).aggregate(v=Coalesce(Sum(_line_profit()), ZERO))['v']

        def order_count(start, end):
            return completed.filter(
                created_at__date__gte=start, created_at__date__lte=end
            ).count()

        low_stock_count = Product.objects.filter(
            is_active=True, quantity__lte=F('reorder_level')
        ).count()
        inventory_value = Product.objects.aggregate(
            v=Coalesce(Sum(F('quantity') * F('cost_price'), output_field=DEC), ZERO)
        )['v']

        payload = {'role': role}

        # ---- KPIs -------------------------------------------------------
        if role == 'staff':
            orders_today = Order.objects.filter(created_at__date=today).count()
            orders_yest = Order.objects.filter(created_at__date=yesterday).count()
            cust_today = Customer.objects.filter(created_at__date=today).count()
            cust_yest = Customer.objects.filter(created_at__date=yesterday).count()
            in_today = StockIn.objects.filter(created_at__date=today).count()
            in_yest = StockIn.objects.filter(created_at__date=yesterday).count()
            out_today = StockOut.objects.filter(created_at__date=today).count()
            out_yest = StockOut.objects.filter(created_at__date=yesterday).count()
            payload['kpis'] = {
                'orders_today': {'value': orders_today, **_delta(orders_today, orders_yest)},
                'customers_today': {'value': cust_today, **_delta(cust_today, cust_yest)},
                'stock_in_today': {'value': in_today, **_delta(in_today, in_yest)},
                'stock_out_today': {'value': out_today, **_delta(out_today, out_yest)},
            }
        elif role == 'manager':
            payload['kpis'] = {
                'total_orders': {'value': order_count(d30, today),
                                 **_delta(order_count(d30, today), order_count(p30s, p30e))},
                'inventory_value': {'value': inventory_value},
                'low_stock_items': {'value': low_stock_count},
                'monthly_sales': {'value': revenue(month_start, today),
                                  **_delta(revenue(month_start, today), revenue(last_month_start, last_month_end))},
            }
        else:  # admin
            payload['kpis'] = {
                'total_sales': {'value': revenue(d7, today),
                                **_delta(revenue(d7, today), revenue(p7s, p7e))},
                'gross_profit': {'value': profit(d7, today),
                                 **_delta(profit(d7, today), profit(p7s, p7e))},
                'orders': {'value': order_count(d7, today),
                           **_delta(order_count(d7, today), order_count(p7s, p7e))},
                'low_stock_items': {'value': low_stock_count},
            }

        # ---- Sales trend (last 7 days, zero-filled) ---------------------
        if role in ('admin', 'manager'):
            rows = {r['day']: r['revenue'] for r in (
                items.filter(order__created_at__date__gte=d7)
                .annotate(day=TruncDate('order__created_at')).values('day')
                .annotate(revenue=Coalesce(Sum(_line_revenue()), ZERO))
            )}
            payload['sales_trend'] = [
                {'day': (d7 + timedelta(days=i)).isoformat(),
                 'revenue': rows.get(d7 + timedelta(days=i), Decimal('0'))}
                for i in range(7)
            ]
            payload['top_products'] = self._top_products(request, items)
            payload['low_stock'] = self._low_stock()

        if role == 'admin':
            payload['recent_activity'] = self._recent_activity()
        if role in ('manager', 'staff'):
            payload['recent_orders'] = self._recent_orders()
        if role == 'staff':
            payload['recent_movements'] = self._recent_movements(request)

        return Response(payload)

    def _top_products(self, request, items):
        rows = list(
            items.values('product__name', 'product__sku', 'product__image')
            .annotate(sold=Sum('quantity'), revenue=Coalesce(Sum(_line_revenue()), ZERO))
            .order_by('-sold')[:5]
        )
        out = []
        for r in rows:
            img = r['product__image']
            out.append({
                'name': r['product__name'],
                'sku': r['product__sku'],
                'image': request.build_absolute_uri(settings.MEDIA_URL + img) if img else None,
                'sold': r['sold'],
                'revenue': r['revenue'],
            })
        return out

    def _low_stock(self):
        products = Product.objects.filter(
            is_active=True, quantity__lte=F('reorder_level')
        ).order_by('quantity')[:6]
        return [{
            'name': p.name, 'sku': p.sku, 'quantity': p.quantity,
            'reorder_level': p.reorder_level,
            'status': ('critical' if p.quantity == 0 or p.quantity <= p.reorder_level / 2
                       else 'low'),
        } for p in products]

    def _recent_orders(self):
        orders = (Order.objects.select_related('customer')
                  .prefetch_related('items').order_by('-created_at')[:6])
        return [{
            'reference': o.reference,
            'customer': o.customer.name if o.customer else 'Walk-in',
            'date': o.created_at.isoformat(),
            'amount': o.total,
            'items_count': o.items.count(),
            'status': o.status,
        } for o in orders]

    def _recent_movements(self, request):
        ins = list(StockInItem.objects.select_related('stock_in', 'product')
                   .order_by('-stock_in__created_at')[:8])
        outs = list(StockOutItem.objects.select_related('stock_out', 'product')
                    .order_by('-stock_out__created_at')[:8])
        rows = []
        for it in ins:
            rows.append({
                'product': it.product.name, 'sku': it.product.sku, 'type': 'in',
                'quantity': it.quantity, 'reference': it.stock_in.reference,
                'created_at': it.stock_in.created_at.isoformat(),
            })
        for it in outs:
            rows.append({
                'product': it.product.name, 'sku': it.product.sku, 'type': 'out',
                'quantity': it.quantity, 'reference': it.stock_out.reference,
                'created_at': it.stock_out.created_at.isoformat(),
            })
        rows.sort(key=lambda r: r['created_at'], reverse=True)
        return rows[:6]

    def _recent_activity(self):
        feed = []
        for o in Order.objects.select_related('customer').order_by('-created_at')[:4]:
            who = o.customer.name if o.customer else 'a walk-in customer'
            feed.append({'type': 'order', 'text': f'New order {o.reference} placed by {who}',
                         'at': o.created_at.isoformat()})
        for s in StockIn.objects.order_by('-created_at')[:3]:
            feed.append({'type': 'stock', 'text': f'Stock received — {s.reference}',
                         'at': s.created_at.isoformat()})
        for s in StockOut.objects.order_by('-created_at')[:2]:
            feed.append({'type': 'stock_out', 'text': f'Stock out recorded — {s.reference}',
                         'at': s.created_at.isoformat()})
        feed.sort(key=lambda r: r['at'], reverse=True)
        return feed[:6]


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
