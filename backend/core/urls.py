from django.urls import path
from .views import DashboardMetricsView, UniversalAnalyzeView, AllHistoryView

urlpatterns = [
    path('dashboard-metrics', DashboardMetricsView.as_view(), name='dashboard-metrics'),
    path('all-history', AllHistoryView.as_view(), name='all-history'),
    path('intelligence/analyze', UniversalAnalyzeView.as_view(), name='intelligence-analyze'),
]
