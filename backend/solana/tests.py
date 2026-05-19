from rest_framework.test import APITestCase
from unittest.mock import patch

class SolanaStage2Tests(APITestCase):
    def test_solana_wallet_validation_invalid(self):
        response = self.client.post('/api/solana/analyze-wallet', {"wallet_address": "invalid"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])

    def test_solana_transaction_validation_invalid(self):
        response = self.client.post('/api/solana/translate-transaction', {"signature": "short"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])

    @patch('solana.services.solana_service.SolanaService.get_wallet_info')
    @patch('ai.services.gemma_service.GemmaService._call_ai')
    def test_solana_wallet_analysis_success(self, mock_ai, mock_solana):
        mock_solana.return_value = {
            "balance": 10**9, # 1 SOL
            "signatures": [{"signature": "sig1"}]
        }
        mock_ai.return_value = "AI summary for Solana wallet."
        
        response = self.client.post('/api/solana/analyze-wallet', {"wallet_address": "HN7cABqL36BJ7n6pEJzWvz9u73E18V6fQ4Bf3j7eC9y2"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['metrics']['balance'], 1.0)
