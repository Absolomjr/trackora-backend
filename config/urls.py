"""Root URL configuration for the Trackora backend."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(request):
    return JsonResponse({'status': 'ok', 'service': 'trackora-backend'})


urlpatterns = [
    path('', health, name='health'),
    path('admin/', admin.site.urls),

    # Auth & user management
    path('api/auth/', include('apps.accounts.urls')),

    # Core resources
    path('api/', include('apps.inventory.urls')),   # categories, suppliers, products
    path('api/', include('apps.stock.urls')),       # stock-in, stock-out
    path('api/', include('apps.sales.urls')),       # customers, orders

    # Reporting
    path('api/reports/', include('apps.reports.urls')),

    # Public marketing site (landing-page account & demo requests)
    path('api/', include('apps.leads.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
