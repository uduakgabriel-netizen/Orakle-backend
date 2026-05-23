from django.urls import path
from .views import DashboardMetricsView, UniversalAnalyzeView, AllHistoryView, AnalysisDetailView

urlpatterns = [
    path('dashboard-metrics', DashboardMetricsView.as_view(), name='dashboard-metrics'),
    path('all-history', AllHistoryView.as_view(), name='all-history'),
    path('analysis-detail/<str:analysis_type>/<int:analysis_id>', AnalysisDetailView.as_view(), name='analysis-detail'),
    path('intelligence/analyze', UniversalAnalyzeView.as_view(), name='intelligence-analyze'),
]
