from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.inventory.models import Product, Supplier


class StockIn(models.Model):
    """A stock receipt — one or more products coming into the store."""

    reference = models.CharField(max_length=40, unique=True, blank=True)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='stock_ins',
    )
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='stock_ins',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stock In'
        verbose_name_plural = 'Stock Ins'

    def __str__(self):
        return f'StockIn {self.reference}'

    @property
    def total_cost(self):
        return sum((item.subtotal for item in self.items.all()), 0)


class StockInItem(models.Model):
    stock_in = models.ForeignKey(StockIn, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='stock_in_items')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    def __str__(self):
        return f'{self.product.name} x{self.quantity}'

    @property
    def subtotal(self):
        return self.quantity * self.unit_cost


class StockOut(models.Model):
    """Stock leaving the store for a non-sale reason (damage, adjustment, etc.)."""

    class Reason(models.TextChoices):
        DAMAGE = 'damage', 'Damaged / Spoiled'
        RETURN = 'return', 'Returned to Supplier'
        ADJUSTMENT = 'adjustment', 'Stock Adjustment'
        INTERNAL = 'internal', 'Internal Use'
        LOST = 'lost', 'Lost / Theft'

    reference = models.CharField(max_length=40, unique=True, blank=True)
    reason = models.CharField(max_length=20, choices=Reason.choices, default=Reason.ADJUSTMENT)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='stock_outs',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stock Out'
        verbose_name_plural = 'Stock Outs'

    def __str__(self):
        return f'StockOut {self.reference} ({self.reason})'


class StockOutItem(models.Model):
    stock_out = models.ForeignKey(StockOut, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='stock_out_items')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    def __str__(self):
        return f'{self.product.name} x{self.quantity}'
