from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.inventory.models import Category, Product
from apps.sales.models import Customer, Order, OrderItem

User = get_user_model()


class RoleOverviewTests(APITestCase):
    url = '/api/reports/overview/'

    def setUp(self):
        self.admin = User.objects.create_user(email='a@t.test', password='pw', role='admin')
        self.manager = User.objects.create_user(email='m@t.test', password='pw', role='manager')
        self.staff = User.objects.create_user(email='s@t.test', password='pw', role='staff')

        cat = Category.objects.create(name='Cement')
        self.p = Product.objects.create(
            name='UltraTech 50kg', sku='UTC-50', category=cat,
            cost_price=30000, selling_price=35000, quantity=4, reorder_level=20,
        )
        cust = Customer.objects.create(name='Shree Balaji')
        order = Order.objects.create(customer=cust, status=Order.Status.COMPLETED, created_by=self.staff)
        OrderItem.objects.create(order=order, product=self.p, quantity=2,
                                 unit_price=35000, unit_cost=30000)

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_payload_shape(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['role'], 'admin')
        for k in ('total_sales', 'gross_profit', 'orders', 'low_stock_items'):
            self.assertIn(k, res.data['kpis'])
        self.assertIn('sales_trend', res.data)
        self.assertEqual(len(res.data['sales_trend']), 7)
        self.assertIn('top_products', res.data)
        self.assertIn('recent_activity', res.data)
        # low-stock product should be flagged
        self.assertTrue(any(x['sku'] == 'UTC-50' for x in res.data['low_stock']))

    def test_manager_payload_shape(self):
        self.client.force_authenticate(self.manager)
        res = self.client.get(self.url)
        self.assertEqual(res.data['role'], 'manager')
        for k in ('total_orders', 'inventory_value', 'low_stock_items', 'monthly_sales'):
            self.assertIn(k, res.data['kpis'])
        self.assertIn('recent_orders', res.data)

    def test_staff_payload_shape(self):
        self.client.force_authenticate(self.staff)
        res = self.client.get(self.url)
        self.assertEqual(res.data['role'], 'staff')
        for k in ('orders_today', 'customers_today', 'stock_in_today', 'stock_out_today'):
            self.assertIn(k, res.data['kpis'])
        self.assertIn('recent_movements', res.data)
        self.assertIn('recent_orders', res.data)
        # staff must NOT receive manager-only widgets
        self.assertNotIn('top_products', res.data)

    def test_kpi_delta_structure(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get(self.url)
        sales = res.data['kpis']['total_sales']
        self.assertIn('value', sales)
        self.assertIn('pct', sales)
        self.assertIn('direction', sales)
