from django.contrib import admin

from .models import Customer, Order, OrderItem


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'created_at')
    search_fields = ('name', 'phone', 'email')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'unit_price', 'unit_cost')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('reference', 'customer', 'status', 'payment_method', 'created_by', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('reference', 'customer__name')
    readonly_fields = ('reference', 'created_by', 'created_at', 'updated_at')
    inlines = [OrderItemInline]

    def has_add_permission(self, request):
        # Orders mutate stock through the API; don't create them here.
        return False
