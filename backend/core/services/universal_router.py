"""
Universal Intelligence Router

Orchestrates the complete analysis pipeline by:
    1. Classifying user input (text or file)
    2. Detecting Ethereum address type via on-chain bytecode
    3. Routing to the correct domain-specific analysis engine
    4. Enriching results with AI interpretation
    5. Returning a standardized response

This powers the single POST /api/intelligence/analyze endpoint.
"""

import logging

from core.services.input_classifier import InputClassifier
from core.services.address_detector import AddressDetectorService
from wallets.services.analysis import WalletAnalyzerService
from contracts.services.analysis import ContractAnalyzerService
from contracts.services.file_analysis import FileAnalysisService
from transactions.services.analysis import TransactionTranslatorService
from solana.services.analysis import SolanaAnalyzerService
from ai.services.gemma_service import GemmaService

logger = logging.getLogger('core')


class UniversalRouterService:
    """
    Central intelligence router. Accepts any blockchain input and returns
    a standardized analysis response.
    """

    def __init__(self):
        self.classifier = InputClassifier()
        self.address_detector = AddressDetectorService()
        self.ai_service = GemmaService()

    def analyze(self, raw_input=None, uploaded_file=None):
        """
        Main entrypoint. Accepts raw text input or an uploaded file.

        Returns:
            dict: Standardized response conforming to the Orakle API schema.
        """
        # --- File Upload Path ---
        if uploaded_file:
            return self._handle_file_upload(uploaded_file)

        # --- Text Input Path ---
        if not raw_input or not isinstance(raw_input, str) or not raw_input.strip():
            return self._error_response(
                message="Input is required. Provide an address, transaction hash, or upload a .sol file.",
                status_code=400
            )

        classification = self.classifier.classify(raw_input)
        input_type = classification["input_type"]
        value = classification["value"]
        chain = classification["chain"]

        logger.info(
            "Universal router: input_type=%s chain=%s value=%s",
            input_type, chain, value[:20] if value else "N/A"
        )

        # --- Ethereum Address (wallet or contract detection) ---
        if input_type == "ethereum_address":
            return self._handle_ethereum_address(value)

        # --- Ethereum Transaction Hash ---
        if input_type == "ethereum_tx_hash":
            return self._handle_ethereum_transaction(value)

        # --- Solana Address ---
        if input_type == "solana_address":
            return self._handle_solana_address(value)

        # --- Solana Signature ---
        if input_type == "solana_signature":
            return self._handle_solana_transaction(value)

        # --- Unknown ---
        return self._error_response(
            message=(
                "Unrecognized input. Please provide a valid Ethereum address, "
                "Ethereum transaction hash, Solana address, Solana signature, "
                "or upload a .sol file."
            ),
            status_code=400
        )

    # ──────────────────────────── ETHEREUM ADDRESS ────────────────────────────

    def _handle_ethereum_address(self, address):
        """
        Detect wallet vs contract via on-chain bytecode, then route to
        the appropriate analysis engine.
        """
        detection = self.address_detector.detect_address_type(address)
        detected_type = detection["type"]
        checksum_address = detection.get("address", address)

        if detected_type == "invalid":
            error_msg = detection.get("error", "Invalid Ethereum address.")
            return self._error_response(message=error_msg, status_code=400)

        if detected_type == "contract":
            return self._analyze_ethereum_contract(checksum_address)

        # Default: wallet (EOA)
        return self._analyze_ethereum_wallet(checksum_address)

    def _analyze_ethereum_wallet(self, address):
        """Run Ethereum wallet analysis pipeline."""
        try:
            service = WalletAnalyzerService()
            result = service.analyze(address)

            if not result.get("success"):
                return self._error_response(
                    message=result.get("error", "Wallet analysis failed."),
                    status_code=400
                )

            analysis_data = result["data"]

            # AI enrichment
            ai_summary = self.ai_service.explain_wallet({
                "chain": "ethereum",
                "address": address,
                "risk_score": analysis_data.get("risk_score"),
                "signals": analysis_data.get("signals", []),
                "metrics": analysis_data.get("metrics", {})
            })

            return self._success_response(
                response_type="wallet",
                chain="ethereum",
                data=analysis_data,
                ai_summary=ai_summary,
                message="Ethereum wallet analysis complete."
            )

        except Exception as e:
            logger.error("Ethereum wallet analysis failed for %s: %s", address, e)
            return self._error_response(
                message="An internal error occurred during wallet analysis.",
                status_code=500
            )

    def _analyze_ethereum_contract(self, address):
        """Run Ethereum contract analysis pipeline."""
        try:
            service = ContractAnalyzerService()
            result = service.analyze(address)

            if not result.get("success"):
                return self._error_response(
                    message=result.get("error", "Contract analysis failed."),
                    status_code=400
                )

            analysis_data = result["data"]

            # AI enrichment
            ai_summary = self.ai_service.explain_contract({
                "chain": "ethereum",
                "address": address,
                "detected_functions": analysis_data.get("detected_functions", []),
                "risk_flags": analysis_data.get("risk_flags", []),
                "risk_score": analysis_data.get("risk_score")
            })

            return self._success_response(
                response_type="contract",
                chain="ethereum",
                data=analysis_data,
                ai_summary=ai_summary,
                message="Ethereum smart contract analysis complete."
            )

        except Exception as e:
            logger.error("Ethereum contract analysis failed for %s: %s", address, e)
            return self._error_response(
                message="An internal error occurred during contract analysis.",
                status_code=500
            )

    # ──────────────────────────── ETHEREUM TRANSACTION ────────────────────────

    def _handle_ethereum_transaction(self, tx_hash):
        """Run Ethereum transaction translation pipeline."""
        try:
            service = TransactionTranslatorService()
            result = service.translate(tx_hash)

            if not result.get("success"):
                return self._error_response(
                    message=result.get("error", "Transaction translation failed."),
                    status_code=400
                )

            analysis_data = result["data"]

            # AI enrichment
            ai_summary = self.ai_service.translate_transaction({
                "chain": "ethereum",
                "tx_hash": tx_hash,
                "type": analysis_data.get("type"),
                "from": analysis_data.get("from"),
                "to": analysis_data.get("to"),
                "value": analysis_data.get("value"),
                "summary": analysis_data.get("summary")
            })

            return self._success_response(
                response_type="transaction",
                chain="ethereum",
                data=analysis_data,
                ai_summary=ai_summary,
                message="Ethereum transaction translation complete."
            )

        except Exception as e:
            logger.error("Ethereum transaction translation failed for %s: %s", tx_hash, e)
            return self._error_response(
                message="An internal error occurred during transaction translation.",
                status_code=500
            )

    # ──────────────────────────── SOLANA ADDRESS ──────────────────────────────

    def _handle_solana_address(self, address):
        """Run Solana wallet analysis pipeline."""
        try:
            service = SolanaAnalyzerService()
            result = service.analyze_wallet(address)

            if not result.get("success"):
                return self._error_response(
                    message=result.get("error", "Solana wallet analysis failed."),
                    status_code=400
                )

            analysis_data = result["data"]

            return self._success_response(
                response_type="solana_wallet",
                chain="solana",
                data=analysis_data,
                ai_summary=analysis_data.get("ai_summary", ""),
                message="Solana wallet analysis complete."
            )

        except Exception as e:
            logger.error("Solana wallet analysis failed for %s: %s", address, e)
            return self._error_response(
                message="An internal error occurred during Solana wallet analysis.",
                status_code=500
            )

    # ──────────────────────────── SOLANA TRANSACTION ──────────────────────────

    def _handle_solana_transaction(self, signature):
        """Run Solana transaction translation pipeline."""
        try:
            service = SolanaAnalyzerService()
            result = service.translate_transaction(signature)

            if not result.get("success"):
                return self._error_response(
                    message=result.get("error", "Solana transaction translation failed."),
                    status_code=400
                )

            analysis_data = result["data"]

            return self._success_response(
                response_type="solana_transaction",
                chain="solana",
                data=analysis_data,
                ai_summary=analysis_data.get("interpretation", ""),
                message="Solana transaction translation complete."
            )

        except Exception as e:
            logger.error("Solana transaction translation failed for %s: %s", signature, e)
            return self._error_response(
                message="An internal error occurred during Solana transaction translation.",
                status_code=500
            )

    # ──────────────────────────── FILE UPLOAD ─────────────────────────────────

    def _handle_file_upload(self, uploaded_file):
        """Handle .sol file upload and analysis."""
        file_classification = self.classifier.classify_file(uploaded_file)

        if file_classification["input_type"] != "solidity_file":
            return self._error_response(
                message=file_classification.get("error", "Unsupported file type."),
                status_code=400
            )

        try:
            service = FileAnalysisService()
            result = service.analyze_solidity_file(uploaded_file)

            if not result.get("success"):
                return self._error_response(
                    message=result.get("error", "Solidity file analysis failed."),
                    status_code=400
                )

            analysis_data = result["data"]

            return self._success_response(
                response_type="contract_file",
                chain="ethereum",
                data=analysis_data,
                ai_summary=analysis_data.get("ai_summary", ""),
                message="Solidity file analysis complete."
            )

        except Exception as e:
            logger.error("Solidity file analysis failed for %s: %s", uploaded_file.name, e)
            return self._error_response(
                message="An internal error occurred during file analysis.",
                status_code=500
            )

    # ──────────────────────────── RESPONSE BUILDERS ───────────────────────────

    @staticmethod
    def _success_response(response_type, chain, data, ai_summary="", message="", visualization=None):
        """Build a standardized success response."""
        return {
            "success": True,
            "type": response_type,
            "chain": chain,
            "data": data,
            "ai_summary": ai_summary,
            "visualization": visualization or {},
            "report_available": True,
            "message": message,
            "status_code": 200
        }

    @staticmethod
    def _error_response(message, status_code=400):
        """Build a standardized error response."""
        return {
            "success": False,
            "type": None,
            "chain": None,
            "data": {},
            "ai_summary": "",
            "visualization": {},
            "report_available": False,
            "message": message,
            "status_code": status_code
        }
