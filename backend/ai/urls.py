from django.urls import path
from .views import AIWalletAnalysisView, AIContractAnalysisView, AITransactionTranslateView

urlpatterns = [
    path('ai/analyze-wallet', AIWalletAnalysisView.as_view(), name='ai-analyze-wallet'),
    path('ai/analyze-contract', AIContractAnalysisView.as_view(), name='ai-analyze-contract'),
    path('ai/analyze-transaction', AITransactionTranslateView.as_view(), name='ai-analyze-transaction'),
]
