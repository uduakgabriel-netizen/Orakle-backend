from rest_framework.test import APITestCase
from unittest.mock import patch

class AIEndpointTests(APITestCase):
    @patch('ai.services.gemma_service.GemmaService._call_ai')
    def test_gemma_service_explain_wallet(self, mock_call_ai):
        mock_call_ai.return_value = "Mocked AI explanation."
        from ai.services.gemma_service import GemmaService
        
        service = GemmaService()
        result = service.explain_wallet({"risk_score": 50, "signals": []})
        self.assertEqual(result, "Mocked AI explanation.")
        mock_call_ai.assert_called_once()
