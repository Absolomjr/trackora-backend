from django.contrib import admin

from .models import StockIn, StockInItem, StockOut, StockOutItem


class StockInItemInline(admin.TabularInline):
    model = StockInItem
    extra = 1
    autocomplete_fields = ('product',)


class StockOutItemInline(admin.TabularInline):
    model = StockOutItem
    extra = 1
    autocomplete_fields = ('product',)


class ReadOnlyMovementAdmin(admin.ModelAdmin):
    """
    Stock movements are view-only in the admin: their quantity side effects
    live in the API serializers, so adding/editing them here would desync
    product counts. Record movements through the API instead.
    """
    readonly_fields = ('created_by', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StockIn)
class StockInAdmin(ReadOnlyMovementAdmin):
    list_display = ('reference', 'supplier', 'created_by', 'created_at')
    list_filter = ('supplier', 'created_at')
    search_fields = ('reference', 'note')
    inlines = [StockInItemInline]


@admin.register(StockOut)
class StockOutAdmin(ReadOnlyMovementAdmin):
    list_display = ('reference', 'reason', 'created_by', 'created_at')
    list_filter = ('reason', 'created_at')
    search_fields = ('reference', 'note')
    inlines = [StockOutItemInline]
