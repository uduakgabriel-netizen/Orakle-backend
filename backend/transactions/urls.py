from django.urls import path
from .views import TransactionTranslateView

urlpatterns = [
    path('translate-transaction', TransactionTranslateView.as_view(), name='translate-transaction'),
]
