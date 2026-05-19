from django.urls import path
from .views import SolanaWalletAnalysisView, SolanaTransactionTranslateView

urlpatterns = [
    path('solana/analyze-wallet', SolanaWalletAnalysisView.as_view(), name='solana-analyze-wallet'),
    path('solana/translate-transaction', SolanaTransactionTranslateView.as_view(), name='solana-translate-transaction'),
]
