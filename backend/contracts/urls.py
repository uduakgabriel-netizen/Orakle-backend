from django.urls import path
from .views import ContractAnalysisView, ContractHistoryView, ContractFileAnalysisView

urlpatterns = [
    path('analyze-contract', ContractAnalysisView.as_view(), name='analyze-contract'),
    path('contract-history/<str:contract_address>', ContractHistoryView.as_view(), name='contract-history'),
    path('analyze-contract-file', ContractFileAnalysisView.as_view(), name='analyze-contract-file'),
]
