from django.urls import path

from .views import (
    BestSellingReportView,
    DailySalesReportView,
    DashboardView,
    LowStockReportView,
    MonthlySalesReportView,
    ProfitReportView,
)

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='report-dashboard'),
    path('low-stock/', LowStockReportView.as_view(), name='report-low-stock'),
    path('daily-sales/', DailySalesReportView.as_view(), name='report-daily-sales'),
    path('monthly-sales/', MonthlySalesReportView.as_view(), name='report-monthly-sales'),
    path('profit/', ProfitReportView.as_view(), name='report-profit'),
    path('best-selling/', BestSellingReportView.as_view(), name='report-best-selling'),
]
