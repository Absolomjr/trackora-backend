from rest_framework.routers import DefaultRouter

from .views import CustomerViewSet, OrderViewSet

router = DefaultRouter()
router.register('customers', CustomerViewSet, basename='customer')
router.register('orders', OrderViewSet, basename='order')

urlpatterns = router.urls
