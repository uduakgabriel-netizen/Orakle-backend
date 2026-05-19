from django.urls import path
from .views import WalletAnalysisView, WalletHistoryView

urlpatterns = [
    path('analyze-wallet', WalletAnalysisView.as_view(), name='analyze-wallet'),
    path('wallet-history/<str:wallet_address>', WalletHistoryView.as_view(), name='wallet-history'),
]
