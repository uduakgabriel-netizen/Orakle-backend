from django.urls import path
from .views import DashboardMetricsView, UniversalAnalyzeView

urlpatterns = [
    path('dashboard-metrics', DashboardMetricsView.as_view(), name='dashboard-metrics'),
    path('intelligence/analyze', UniversalAnalyzeView.as_view(), name='intelligence-analyze'),
]
