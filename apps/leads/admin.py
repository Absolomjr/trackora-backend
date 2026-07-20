from django.contrib import admin

from .models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'business_name', 'kind', 'status', 'created_at')
    list_filter = ('kind', 'status', 'created_at')
    list_editable = ('status',)
    search_fields = ('full_name', 'email', 'phone', 'business_name', 'location')
    readonly_fields = (
        'kind', 'full_name', 'email', 'phone', 'business_name', 'location',
        'message', 'source', 'ip_address', 'user_agent', 'created_at', 'updated_at',
    )
    fieldsets = (
        ('Request', {'fields': ('kind', 'status', 'note')}),
        ('Contact', {'fields': ('full_name', 'email', 'phone', 'business_name', 'location', 'message')}),
        ('Metadata', {
            'classes': ('collapse',),
            'fields': ('source', 'ip_address', 'user_agent', 'created_at', 'updated_at'),
        }),
    )

    def has_add_permission(self, request):
        # Leads arrive from the public form only.
        return False
