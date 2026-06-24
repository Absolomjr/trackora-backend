from django.contrib import admin

from .models import Category, Product, Supplier


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'contact_person', 'phone', 'email')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'sku', 'category', 'quantity', 'reorder_level',
        'cost_price', 'selling_price', 'is_low_stock', 'is_active',
    )
    list_filter = ('category', 'supplier', 'unit', 'is_active')
    search_fields = ('name', 'sku')
    list_select_related = ('category', 'supplier')
    readonly_fields = ('quantity', 'created_at', 'updated_at')

    @admin.display(boolean=True, description='Low stock')
    def is_low_stock(self, obj):
        return obj.is_low_stock
