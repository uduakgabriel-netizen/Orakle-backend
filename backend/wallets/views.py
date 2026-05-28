import re
from rest_framework.views import APIView
from .services.analysis import WalletAnalyzerService
from .models import WalletAnalysis
from core.utils import standardized_response

class WalletAnalysisView(APIView):
    def post(self, request):
        address = request.data.get('wallet_address')
        if not address:
            return standardized_response(success=False, message="wallet_address is required", status_code=400)
        
        if not isinstance(address, str) or not re.match(r'^0x[a-fA-F0-9]{40}$', address):
            return standardized_response(success=False, message="Invalid wallet address", status_code=400)
        
        try:
            service = WalletAnalyzerService()
            result = service.analyze(address)
            
            if result.get('success'):
                return standardized_response(data=result.get('data'), message="Wallet analysis complete")
            return standardized_response(success=False, message=result.get('error'), status_code=400)
        except Exception as e:
            return standardized_response(success=False, message=f"Internal error: {str(e)}", status_code=500)

class WalletHistoryView(APIView):
    def get(self, request, wallet_address):
        if not re.match(r'^0x[a-fA-F0-9]{40}$', wallet_address):
            return standardized_response(success=False, message="Invalid wallet address", status_code=400)
        
        history = WalletAnalysis.objects.filter(wallet_address=wallet_address).order_by('-created_at')
        
        data = []
        evolution = []
        for entry in history:
            data.append({
                "risk_score": entry.risk_score,
                "signals": entry.signals,
                "created_at": entry.created_at,
                "chain": entry.chain
            })
            
            # Evolution summary
            risk_label = "Low Risk"
            if entry.risk_score > 70: risk_label = "High Risk"
            elif entry.risk_score > 40: risk_label = "Medium Risk"
            
            evolution.append(f"{entry.created_at.strftime('%b %d')} → {risk_label}")

        return standardized_response(data={
            "history": data,
            "evolution": evolution[:5] # Last 5 for summary
        }, message="History retrieved successfully")
