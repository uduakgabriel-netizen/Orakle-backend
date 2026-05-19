import logging

from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Count, Q

from .utils import standardized_response
from .services.universal_router import UniversalRouterService
from wallets.models import WalletAnalysis
from contracts.models import ContractAnalysis
from transactions.models import TransactionAnalysis
from reports.models import Report

logger = logging.getLogger('core')


class DashboardMetricsView(APIView):
    def get(self, request):
        try:
            metrics = {
                "wallet_analyses": WalletAnalysis.objects.count(),
                "contract_analyses": ContractAnalysis.objects.count(),
                "transaction_analyses": TransactionAnalysis.objects.count(),
                "reports_generated": Report.objects.count(),
                "high_risk_wallets": WalletAnalysis.objects.filter(risk_score__gt=70).count(),
                "high_risk_contracts": ContractAnalysis.objects.filter(risk_score__gt=70).count(),
            }

            # Optional: Risk Distribution
            wallet_risk_dist = WalletAnalysis.objects.aggregate(
                low=Count('id', filter=Q(risk_score__lte=40)),
                medium=Count('id', filter=Q(risk_score__gt=40, risk_score__lte=70)),
                high=Count('id', filter=Q(risk_score__gt=70))
            )

            metrics["risk_distribution"] = {
                "wallets": wallet_risk_dist
            }

            # Recent activity (bonus)
            recent_wallets = WalletAnalysis.objects.order_by('-created_at')[:5].values('wallet_address', 'risk_score', 'created_at')
            metrics["recent_activity"] = list(recent_wallets)

            return standardized_response(data=metrics, message="Dashboard metrics retrieved successfully")
        except Exception as e:
            return standardized_response(success=False, message=f"Error retrieving metrics: {str(e)}", status_code=500)


class UniversalAnalyzeView(APIView):
    """
    POST /api/intelligence/analyze

    The universal intelligence endpoint. Accepts:
        - JSON body with "input" field (address, tx hash, Solana address/signature)
        - multipart/form-data with "file" field (.sol file upload)

    Automatically detects the input type, routes to the correct analysis engine,
    enriches with AI interpretation, and returns a standardized response.
    """
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request):
        # Check for file upload first
        uploaded_file = request.FILES.get('file')
        raw_input = request.data.get('input', '').strip() if not uploaded_file else None

        # Reject completely empty requests
        if not uploaded_file and not raw_input:
            return standardized_response(
                success=False,
                message=(
                    "Input is required. Send a JSON body with an 'input' field "
                    "(address, tx hash, or Solana identifier) or upload a .sol file "
                    "via the 'file' field."
                ),
                status_code=400
            )

        try:
            router = UniversalRouterService()
            result = router.analyze(raw_input=raw_input, uploaded_file=uploaded_file)

            # Extract status code from router result (default 200)
            status_code = result.pop('status_code', 200)

            return standardized_response(
                success=result.get('success', False),
                data={
                    "type": result.get('type'),
                    "chain": result.get('chain'),
                    "analysis": result.get('data', {}),
                    "ai_summary": result.get('ai_summary', ''),
                    "visualization": result.get('visualization', {}),
                    "report_available": result.get('report_available', False),
                },
                message=result.get('message', ''),
                status_code=status_code
            )

        except Exception as e:
            logger.error("Universal analyze endpoint error: %s", e, exc_info=True)
            return standardized_response(
                success=False,
                message="An internal error occurred. Please try again.",
                status_code=500
            )
