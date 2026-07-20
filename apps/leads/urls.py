from django.urls import path

from .views import LeadCreateView, LeadDetailView, LeadListView

urlpatterns = [
    path('leads/', LeadCreateView.as_view(), name='lead-create'),
    path('leads/all/', LeadListView.as_view(), name='lead-list'),
    path('leads/all/<int:pk>/', LeadDetailView.as_view(), name='lead-detail'),
]
