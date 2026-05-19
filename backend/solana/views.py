from rest_framework.views import APIView
from .services.analysis import SolanaAnalyzerService
from core.utils import standardized_response
import re

class SolanaWalletAnalysisView(APIView):
    def post(self, request):
        address = request.data.get('wallet_address')
        if not address:
            return standardized_response(success=False, message="wallet_address is required", status_code=400)
        
        # Solana address validation (base58, 32-44 chars)
        if not re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
            return standardized_response(success=False, message="Invalid Solana wallet address", status_code=400)
        
        try:
            service = SolanaAnalyzerService()
            result = service.analyze_wallet(address)
            
            if result.get('success'):
                return standardized_response(data=result.get('data'), message="Solana wallet analyzed successfully")
            return standardized_response(success=False, message=result.get('error'), status_code=400)
        except Exception as e:
            return standardized_response(success=False, message=f"Internal error: {str(e)}", status_code=500)

class SolanaTransactionTranslateView(APIView):
    def post(self, request):
        signature = request.data.get('signature')
        if not signature:
            return standardized_response(success=False, message="signature is required", status_code=400)
        
        # Solana signature validation (base58, ~88 chars)
        if not re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,88}$', signature):
            return standardized_response(success=False, message="Invalid Solana transaction signature", status_code=400)

        try:
            service = SolanaAnalyzerService()
            result = service.translate_transaction(signature)
            
            if result.get('success'):
                return standardized_response(data=result.get('data'), message="Solana transaction translated successfully")
            return standardized_response(success=False, message=result.get('error'), status_code=400)
        except Exception as e:
            return standardized_response(success=False, message=f"Internal error: {str(e)}", status_code=500)
