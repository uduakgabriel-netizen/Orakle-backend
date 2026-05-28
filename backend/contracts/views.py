import re
from rest_framework.views import APIView
from .services.analysis import ContractAnalyzerService
from .models import ContractAnalysis
from core.utils import standardized_response

class ContractAnalysisView(APIView):
    def post(self, request):
        address = request.data.get('contract_address')
        if not address:
            return standardized_response(success=False, message="contract_address is required", status_code=400)
        
        if not isinstance(address, str) or not re.match(r'^0x[a-fA-F0-9]{40}$', address):
            return standardized_response(success=False, message="Invalid contract address", status_code=400)
        
        try:
            service = ContractAnalyzerService()
            result = service.analyze(address)
            
            if result.get('success'):
                return standardized_response(data=result.get('data'), message="Contract analysis complete")
            return standardized_response(success=False, message=result.get('error'), status_code=400)
        except Exception as e:
            return standardized_response(success=False, message=f"Internal error: {str(e)}", status_code=500)

class ContractHistoryView(APIView):
    def get(self, request, contract_address):
        if not re.match(r'^0x[a-fA-F0-9]{40}$', contract_address):
            return standardized_response(success=False, message="Invalid contract address", status_code=400)
        
        history = ContractAnalysis.objects.filter(contract_address=contract_address).order_by('-created_at')
        
        data = []
        evolution = []
        for entry in history:
            data.append({
                "risk_score": entry.risk_score,
                "risk_flags": entry.risk_flags,
                "created_at": entry.created_at,
                "metadata": entry.metadata
            })
            
            # Evolution summary
            risk_label = "Low Risk"
            if entry.risk_score > 70: risk_label = "High Risk"
            elif entry.risk_score > 40: risk_label = "Medium Risk"
            
            evolution.append(f"{entry.created_at.strftime('%b %d')} → {risk_label}")

        return standardized_response(data={
            "history": data,
            "evolution": evolution[:5]
        }, message="History retrieved successfully")

from .services.file_analysis import FileAnalysisService
from rest_framework.parsers import MultiPartParser, FormParser

class ContractFileAnalysisView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        uploaded_file = request.FILES.get('contract_file')
        
        if not uploaded_file:
            return standardized_response(success=False, message="contract_file is required", status_code=400)

        if not uploaded_file.name.endswith('.sol'):
            return standardized_response(success=False, message="Only .sol files are accepted", status_code=400)

        # Limit size to 1MB for safety
        if uploaded_file.size > 1 * 1024 * 1024:
            return standardized_response(success=False, message="File size exceeds 1MB limit", status_code=400)

        try:
            service = FileAnalysisService()
            result = service.analyze_solidity_file(uploaded_file)
            
            if result.get('success'):
                return standardized_response(data=result.get('data'), message="Solidity contract analyzed successfully")
            return standardized_response(success=False, message=result.get('error'), status_code=400)
        except Exception as e:
            return standardized_response(success=False, message=f"An internal error occurred during file analysis: {str(e)}", status_code=500)
