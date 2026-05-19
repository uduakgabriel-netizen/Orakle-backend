import re
from rest_framework.views import APIView
from .services.analysis import TransactionTranslatorService
from core.utils import standardized_response

class TransactionTranslateView(APIView):
    def post(self, request):
        tx_hash = request.data.get('tx_hash')
        if not tx_hash:
            return standardized_response(success=False, message="tx_hash is required", status_code=400)
        
        if not isinstance(tx_hash, str) or not re.match(r'^0x[a-fA-F0-9]{64}$', tx_hash):
            return standardized_response(success=False, message="Invalid transaction hash", status_code=400)
        
        try:
            service = TransactionTranslatorService()
            result = service.translate(tx_hash)
            
            if result.get('success'):
                return standardized_response(data=result.get('data'), message="Transaction translation complete")
            return standardized_response(success=False, message=result.get('error'), status_code=400)
        except Exception as e:
            return standardized_response(success=False, message="An internal error occurred during transaction translation.", status_code=500)
