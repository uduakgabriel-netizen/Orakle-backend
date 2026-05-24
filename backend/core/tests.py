"""
Comprehensive test suite for the Universal Intelligence Router.

Tests:
    - Input classification (ETH address, tx hash, Solana address/sig, file)
    - Address detection (wallet, contract, invalid)
    - Universal router endpoint (all input types)
    - Error handling (RPC failures, malformed inputs, empty requests)
    - Response schema consistency
"""

import json
from io import BytesIO
from unittest.mock import patch, MagicMock

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from core.services.input_classifier import InputClassifier
from core.services.address_detector import AddressDetectorService


# ═══════════════════════════════════════════════════════════════════════════════
# INPUT CLASSIFIER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class InputClassifierTests(APITestCase):
    """Tests for deterministic input classification."""

    def test_classify_ethereum_address(self):
        result = InputClassifier.classify("0xdAC17F958D2ee523a2206206994597C13D831ec7")
        self.assertEqual(result["input_type"], "ethereum_address")
        self.assertEqual(result["chain"], "ethereum")

    def test_classify_ethereum_address_lowercase(self):
        result = InputClassifier.classify("0xdac17f958d2ee523a2206206994597c13d831ec7")
        self.assertEqual(result["input_type"], "ethereum_address")
        self.assertEqual(result["chain"], "ethereum")

    def test_classify_ethereum_tx_hash(self):
        tx = "0x" + "a" * 64
        result = InputClassifier.classify(tx)
        self.assertEqual(result["input_type"], "ethereum_tx_hash")
        self.assertEqual(result["chain"], "ethereum")

    def test_classify_ethereum_tx_hash_real(self):
        tx = "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060"
        result = InputClassifier.classify(tx)
        self.assertEqual(result["input_type"], "ethereum_tx_hash")
        self.assertEqual(result["chain"], "ethereum")

    def test_classify_solana_address(self):
        result = InputClassifier.classify("So11111111111111111111111111111111111111112")
        self.assertEqual(result["input_type"], "solana_address")
        self.assertEqual(result["chain"], "solana")

    def test_classify_solana_signature(self):
        # Typical Solana signature is 87-88 chars
        sig = "5" * 88
        result = InputClassifier.classify(sig)
        self.assertEqual(result["input_type"], "solana_signature")
        self.assertEqual(result["chain"], "solana")

    def test_classify_unknown_input(self):
        result = InputClassifier.classify("hello world")
        self.assertEqual(result["input_type"], "unknown")
        self.assertIsNone(result["chain"])

    def test_classify_empty_string(self):
        result = InputClassifier.classify("")
        self.assertEqual(result["input_type"], "unknown")

    def test_classify_none(self):
        result = InputClassifier.classify(None)
        self.assertEqual(result["input_type"], "unknown")

    def test_classify_whitespace_stripped(self):
        result = InputClassifier.classify("  0xdAC17F958D2ee523a2206206994597C13D831ec7  ")
        self.assertEqual(result["input_type"], "ethereum_address")

    def test_classify_sol_file(self):
        content = b"pragma solidity ^0.8.0; contract Test {}"
        file = SimpleUploadedFile("test.sol", content, content_type="text/plain")
        result = InputClassifier.classify_file(file)
        self.assertEqual(result["input_type"], "solidity_file")
        self.assertEqual(result["chain"], "ethereum")
        self.assertIsNone(result["error"])

    def test_classify_non_sol_file(self):
        file = SimpleUploadedFile("test.txt", b"hello", content_type="text/plain")
        result = InputClassifier.classify_file(file)
        self.assertEqual(result["input_type"], "unknown")
        self.assertIn("Unsupported file type", result["error"])

    def test_classify_oversized_file(self):
        content = b"x" * (2 * 1024 * 1024)  # 2MB
        file = SimpleUploadedFile("big.sol", content, content_type="text/plain")
        result = InputClassifier.classify_file(file)
        self.assertEqual(result["input_type"], "unknown")
        self.assertIn("1MB", result["error"])

    def test_classify_no_file(self):
        result = InputClassifier.classify_file(None)
        self.assertEqual(result["input_type"], "unknown")
        self.assertIn("No file", result["error"])


# ═══════════════════════════════════════════════════════════════════════════════
# ADDRESS DETECTOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class AddressDetectorTests(APITestCase):
    """Tests for blockchain-backed address type detection."""

    def test_validate_valid_address(self):
        self.assertTrue(
            AddressDetectorService.validate_address("0xdAC17F958D2ee523a2206206994597C13D831ec7")
        )

    def test_validate_invalid_address(self):
        self.assertFalse(AddressDetectorService.validate_address("not-an-address"))

    def test_validate_empty_address(self):
        self.assertFalse(AddressDetectorService.validate_address(""))

    def test_validate_none_address(self):
        self.assertFalse(AddressDetectorService.validate_address(None))

    def test_validate_short_hex(self):
        self.assertFalse(AddressDetectorService.validate_address("0x1234"))

    def test_checksum_conversion(self):
        result = AddressDetectorService.to_checksum("0xdac17f958d2ee523a2206206994597c13d831ec7")
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("0x"))

    def test_checksum_invalid(self):
        result = AddressDetectorService.to_checksum("invalid")
        self.assertIsNone(result)

    def test_detect_wallet(self):
        """Mock RPC to return empty bytecode → wallet."""
        detector = AddressDetectorService()
        detector._w3 = MagicMock()
        detector._w3.eth.get_code.return_value = b''

        result = detector.detect_address_type("0xdAC17F958D2ee523a2206206994597C13D831ec7")
        self.assertEqual(result["type"], "wallet")
        self.assertIsNone(result["error"])

    def test_detect_contract(self):
        """Mock RPC to return non-empty bytecode → contract."""
        detector = AddressDetectorService()
        detector._w3 = MagicMock()
        detector._w3.eth.get_code.return_value = b'\x60\x80\x60\x40'

        result = detector.detect_address_type("0xdAC17F958D2ee523a2206206994597C13D831ec7")
        self.assertEqual(result["type"], "contract")
        self.assertIsNone(result["error"])

    def test_detect_invalid_address(self):
        detector = AddressDetectorService()
        result = detector.detect_address_type("0xinvalid")
        self.assertEqual(result["type"], "invalid")
        self.assertIsNotNone(result["error"])

    def test_detect_rpc_failure(self):
        """Simulate RPC failure during detection."""
        detector = AddressDetectorService()
        detector.rpc_url = "https://fake-rpc.example.com"
        detector._w3 = MagicMock()
        detector._w3.eth.get_code.side_effect = Exception("RPC timeout")

        result = detector.detect_address_type("0xdAC17F958D2ee523a2206206994597C13D831ec7")
        self.assertEqual(result["type"], "invalid")
        self.assertIsNotNone(result["error"])


# ═══════════════════════════════════════════════════════════════════════════════
# UNIVERSAL ROUTER ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class UniversalAnalyzeEndpointTests(APITestCase):
    """Integration tests for POST /api/intelligence/analyze."""

    URL = '/api/intelligence/analyze'

    def test_empty_request_rejected(self):
        """Completely empty request must be rejected with 400."""
        response = self.client.post(self.URL, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])

    def test_empty_input_string_rejected(self):
        """Whitespace-only input must be rejected."""
        response = self.client.post(self.URL, {"input": "   "}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])

    def test_unknown_input_rejected(self):
        """Gibberish input must be rejected gracefully."""
        response = self.client.post(self.URL, {"input": "hello world"}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])
        self.assertIn("Unrecognized input", response.data['message'])

    @patch('core.services.universal_router.WalletAnalyzerService')
    @patch('core.services.universal_router.AddressDetectorService')
    def test_wallet_routing(self, MockDetector, MockWallet):
        """Valid ETH address detected as wallet must route to wallet analyzer."""
        MockDetector.return_value.detect_address_type.return_value = {
            "type": "wallet",
            "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "error": None
        }
        MockWallet.return_value.analyze.return_value = {
            "success": True,
            "data": {"risk_score": 25, "signals": [], "metrics": {"tx_count": 42}}
        }

        response = self.client.post(
            self.URL,
            {"input": "0xdAC17F958D2ee523a2206206994597C13D831ec7"},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['type'], 'wallet')
        self.assertEqual(response.data['data']['chain'], 'ethereum')
        self.assertTrue(response.data['data']['report_available'])

    @patch('core.services.universal_router.ContractAnalyzerService')
    @patch('core.services.universal_router.AddressDetectorService')
    def test_contract_routing(self, MockDetector, MockContract):
        """Valid ETH address detected as contract must route to contract analyzer."""
        MockDetector.return_value.detect_address_type.return_value = {
            "type": "contract",
            "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "error": None
        }
        MockContract.return_value.analyze.return_value = {
            "success": True,
            "data": {"risk_score": 65, "detected_functions": ["mint"], "risk_flags": ["Owner can mint"]}
        }

        response = self.client.post(
            self.URL,
            {"input": "0xdAC17F958D2ee523a2206206994597C13D831ec7"},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['type'], 'contract')
        self.assertEqual(response.data['data']['chain'], 'ethereum')

    @patch('core.services.universal_router.TransactionTranslatorService')
    def test_tx_hash_routing(self, MockTx):
        """Valid ETH tx hash must route to transaction translator."""
        tx_hash = "0x" + "a" * 64
        MockTx.return_value.translate.return_value = {
            "success": True,
            "data": {"type": "transfer", "from": "0x1", "to": "0x2", "value": "1.0 ETH", "summary": "Transfer"}
        }

        response = self.client.post(self.URL, {"input": tx_hash}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['type'], 'transaction')
        self.assertEqual(response.data['data']['chain'], 'ethereum')

    @patch('core.services.universal_router.SolanaAnalyzerService')
    def test_solana_address_routing(self, MockSolana):
        """Valid Solana address must route to Solana analyzer."""
        MockSolana.return_value.analyze_wallet.return_value = {
            "success": True,
            "data": {"risk_score": 10, "signals": [], "metrics": {}, "ai_summary": "Clean wallet."}
        }

        response = self.client.post(
            self.URL,
            {"input": "So11111111111111111111111111111111111111112"},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['type'], 'solana_wallet')
        self.assertEqual(response.data['data']['chain'], 'solana')

    @patch('core.services.universal_router.SolanaAnalyzerService')
    def test_solana_signature_routing(self, MockSolana):
        """Valid Solana signature must route to Solana transaction translator."""
        MockSolana.return_value.translate_transaction.return_value = {
            "success": True,
            "data": {"id": 1, "signature": "5" * 88, "interpretation": "Solana transfer."}
        }

        response = self.client.post(
            self.URL,
            {"input": "5" * 88},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['type'], 'solana_transaction')
        self.assertEqual(response.data['data']['chain'], 'solana')

    @patch('core.services.universal_router.FileAnalysisService')
    def test_sol_file_routing(self, MockFile):
        """Uploaded .sol file must route to file analysis service."""
        MockFile.return_value.analyze_solidity_file.return_value = {
            "success": True,
            "data": {
                "risk_score": 30,
                "detected_functions": ["mint"],
                "risk_flags": [],
                "ai_summary": "Simple contract.",
                "report_url": "/media/reports/test.pdf"
            }
        }

        content = b"pragma solidity ^0.8.0; contract Test { function mint() public {} }"
        file = SimpleUploadedFile("test.sol", content, content_type="text/plain")

        response = self.client.post(self.URL, {"file": file}, format='multipart')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['type'], 'contract_file')
        self.assertEqual(response.data['data']['chain'], 'ethereum')

    def test_non_sol_file_rejected(self):
        """Non-.sol file upload must be rejected."""
        file = SimpleUploadedFile("readme.txt", b"hello", content_type="text/plain")
        response = self.client.post(self.URL, {"file": file}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])

    def test_response_schema_consistency(self):
        """Every error response must follow the standardized schema."""
        response = self.client.post(self.URL, {"input": "gibberish"}, format='json')
        data = response.data
        self.assertIn('success', data)
        self.assertIn('data', data)
        self.assertIn('message', data)


# ═══════════════════════════════════════════════════════════════════════════════
# EXISTING DASHBOARD TESTS (preserved)
# ═══════════════════════════════════════════════════════════════════════════════

from wallets.models import WalletAnalysis
from contracts.models import ContractAnalysis


class DashboardMetricsTests(APITestCase):
    def test_dashboard_metrics_aggregation(self):
        WalletAnalysis.objects.create(wallet_address="0x1", risk_score=80)
        WalletAnalysis.objects.create(wallet_address="0x2", risk_score=20)
        ContractAnalysis.objects.create(contract_address="0x3", risk_score=90)

        response = self.client.get('/api/dashboard-metrics')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['wallet_analyses'], 2)
        self.assertEqual(response.data['data']['contract_analyses'], 1)
        self.assertEqual(response.data['data']['high_risk_wallets'], 1)
        self.assertEqual(response.data['data']['high_risk_contracts'], 1)
