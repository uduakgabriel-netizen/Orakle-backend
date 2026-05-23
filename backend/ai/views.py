from rest_framework.views import APIView
from .services.gemma_service import GemmaService
from wallets.models import WalletAnalysis
from contracts.models import ContractAnalysis
from transactions.models import TransactionAnalysis
from core.utils import standardized_response

class AIWalletAnalysisView(APIView):
    def post(self, request):
        wallet_id = request.data.get('id')
        try:
            analysis = WalletAnalysis.objects.get(id=wallet_id)
            structured_data = {
                "wallet_address": analysis.wallet_address,
                "risk_score": analysis.risk_score,
                "signals": analysis.signals,
                "metrics": analysis.raw_metrics
            }
            
            ai_service = GemmaService()
            explanation = ai_service.explain_wallet(structured_data)
            
            response_data = {
                **explanation,
                "ai_summary": explanation
            }
            return standardized_response(data=response_data)
        except WalletAnalysis.DoesNotExist:
            return standardized_response(success=False, message="Analysis not found", status_code=404)

class AIContractAnalysisView(APIView):
    def post(self, request):
        contract_id = request.data.get('id')
        try:
            analysis = ContractAnalysis.objects.get(id=contract_id)
            structured_data = {
                "contract_address": analysis.contract_address,
                "detected_functions": analysis.detected_functions,
                "risk_flags": analysis.risk_flags,
                "risk_score": analysis.risk_score
            }
            
            ai_service = GemmaService()
            explanation = ai_service.explain_contract(structured_data)
            
            response_data = {
                **explanation,
                "ai_summary": explanation
            }
            return standardized_response(data=response_data)
        except ContractAnalysis.DoesNotExist:
            return standardized_response(success=False, message="Analysis not found", status_code=404)

class AITransactionTranslateView(APIView):
    def post(self, request):
        tx_id = request.data.get('id')
        try:
            analysis = TransactionAnalysis.objects.get(id=tx_id)
            # Check if interpretation is already structured JSON (new format)
            if isinstance(analysis.interpretation, dict):
                explanation = analysis.interpretation
            else:
                # Fallback: re-generate or return as summary
                structured_data = {
                    "tx_hash": analysis.tx_hash,
                    "summary": str(analysis.interpretation)
                }
                ai_service = GemmaService()
                explanation = ai_service.translate_transaction(structured_data)
            
            response_data = {
                **explanation,
                "ai_summary": explanation
            }
            return standardized_response(data=response_data)
        except TransactionAnalysis.DoesNotExist:
            return standardized_response(success=False, message="Analysis not found", status_code=404)
