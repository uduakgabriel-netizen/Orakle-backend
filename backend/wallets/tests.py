from rest_framework.test import APITestCase
from .models import WalletAnalysis

class WalletStage2Tests(APITestCase):
    def test_wallet_history_pagination_and_sorting(self):
        addr = "0x" + "2" * 40
        # Create 3 entries
        WalletAnalysis.objects.create(wallet_address=addr, risk_score=10)
        WalletAnalysis.objects.create(wallet_address=addr, risk_score=50)
        WalletAnalysis.objects.create(wallet_address=addr, risk_score=90)
        
        response = self.client.get(f'/api/wallet-history/{addr}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['data']['history']), 3)
        # Check sorting (newest first)
        self.assertEqual(response.data['data']['history'][0]['risk_score'], 90)
        # Check evolution
        self.assertEqual(len(response.data['data']['evolution']), 3)
        self.assertIn("High Risk", response.data['data']['evolution'][0])
