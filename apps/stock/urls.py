from rest_framework.routers import DefaultRouter

from .views import StockInViewSet, StockOutViewSet

router = DefaultRouter()
router.register('stock-in', StockInViewSet, basename='stock-in')
router.register('stock-out', StockOutViewSet, basename='stock-out')

urlpatterns = router.urls
