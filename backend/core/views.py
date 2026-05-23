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

from solana.models import SolanaWalletAnalysis, SolanaTransactionAnalysis

logger = logging.getLogger('core')


class AllHistoryView(APIView):
    """
    GET /api/all-history
    Aggregates history from all analysis models.
    """
    def get(self, request):
        try:
            wallets = WalletAnalysis.objects.all().order_by('-created_at')[:20]
            contracts = ContractAnalysis.objects.all().order_by('-created_at')[:20]
            transactions = TransactionAnalysis.objects.all().order_by('-created_at')[:20]
            solana_wallets = SolanaWalletAnalysis.objects.all().order_by('-created_at')[:20]
            solana_transactions = SolanaTransactionAnalysis.objects.all().order_by('-created_at')[:20]

            history = []

            # Helper to check for report
            def get_report_url(analysis_type, analysis_id):
                report = Report.objects.filter(analysis_type=analysis_type, related_analysis_id=analysis_id).first()
                if report and report.pdf_file:
                    return request.build_absolute_uri(report.pdf_file.url)
                return None

            for w in wallets:
                history.append({
                    "id": w.id,
                    "type": "wallet",
                    "chain": "ethereum",
                    "address": w.wallet_address,
                    "risk_score": w.risk_score,
                    "created_at": w.created_at,
                    "report_url": get_report_url("wallet", w.id)
                })

            for c in contracts:
                history.append({
                    "id": c.id,
                    "type": "contract",
                    "chain": "ethereum",
                    "address": c.contract_address,
                    "risk_score": c.risk_score,
                    "created_at": c.created_at,
                    "report_url": get_report_url("contract", c.id)
                })

            for t in transactions:
                history.append({
                    "id": t.id,
                    "type": "transaction",
                    "chain": "ethereum",
                    "address": t.tx_hash,
                    "risk_score": None,
                    "created_at": t.created_at,
                    "report_url": get_report_url("transaction", t.id)
                })
            
            for s in solana_wallets:
                history.append({
                    "id": s.id,
                    "type": "solana_wallet",
                    "chain": "solana",
                    "address": s.wallet_address,
                    "risk_score": s.risk_score,
                    "created_at": s.created_at,
                    "report_url": get_report_url("solana_wallet", s.id)
                })

            for st in solana_transactions:
                history.append({
                    "id": st.id,
                    "type": "solana_transaction",
                    "chain": "solana",
                    "address": st.signature,
                    "risk_score": None,
                    "created_at": st.created_at,
                    "report_url": get_report_url("solana_transaction", st.id)
                })

            # Sort combined history by date descending
            history.sort(key=lambda x: x['created_at'], reverse=True)

            return standardized_response(data=history[:50], message="All history retrieved successfully")
        except Exception as e:
            logger.error("Error retrieving all history: %s", e)
            return standardized_response(success=False, message=f"Error retrieving history: {str(e)}", status_code=500)


class AnalysisDetailView(APIView):
    """
    GET /api/analysis-detail/<type>/<id>
    Retrieves a previously saved analysis by its specific model type and ID.
    """
    def get(self, request, analysis_type, analysis_id):
        try:
            from wallets.models import WalletAnalysis
            from contracts.models import ContractAnalysis
            from transactions.models import TransactionAnalysis
            from solana.models import SolanaWalletAnalysis, SolanaTransactionAnalysis
            from reports.models import Report

            if analysis_type == 'wallet':
                obj = WalletAnalysis.objects.get(id=analysis_id)
            elif analysis_type == 'contract':
                obj = ContractAnalysis.objects.get(id=analysis_id)
            elif analysis_type == 'transaction':
                obj = TransactionAnalysis.objects.get(id=analysis_id)
            elif analysis_type == 'solana_wallet':
                obj = SolanaWalletAnalysis.objects.get(id=analysis_id)
            elif analysis_type == 'solana_transaction':
                obj = SolanaTransactionAnalysis.objects.get(id=analysis_id)
            else:
                return standardized_response(success=False, message="Invalid analysis type", status_code=400)
            
            # Ensure report_available is updated in the payload if a report exists now
            payload = obj.response_payload.copy() if obj.response_payload else {}
            has_report = Report.objects.filter(analysis_type=analysis_type, related_analysis_id=analysis_id).exists()
            payload['report_available'] = has_report
            
            return standardized_response(data=payload, message="Analysis retrieved successfully")
        except Exception:
            return standardized_response(success=False, message="Analysis not found", status_code=404)


class DashboardMetricsView(APIView):
    def get(self, request):
        try:
            # Count Ethereum analyses
            eth_wallet_count = WalletAnalysis.objects.count()
            eth_contract_count = ContractAnalysis.objects.count()
            eth_tx_count = TransactionAnalysis.objects.count()
            
            # Count Solana analyses
            solana_wallet_count = SolanaWalletAnalysis.objects.count()
            solana_tx_count = SolanaTransactionAnalysis.objects.count()
            
            # Total wallet analyses (Ethereum + Solana)
            total_wallet_analyses = eth_wallet_count + solana_wallet_count
            
            # Total transaction analyses (Ethereum + Solana)
            total_tx_analyses = eth_tx_count + solana_tx_count
            
            metrics = {
                "wallet_analyses": total_wallet_analyses,
                "contract_analyses": eth_contract_count,
                "transaction_analyses": total_tx_analyses,
                "reports_generated": Report.objects.count(),
                "high_risk_wallets": WalletAnalysis.objects.filter(risk_score__gt=70).count() + SolanaWalletAnalysis.objects.filter(risk_score__gt=70).count(),
                "high_risk_contracts": ContractAnalysis.objects.filter(risk_score__gt=70).count(),
            }

            # Optional: Risk Distribution (Ethereum wallets)
            wallet_risk_dist = WalletAnalysis.objects.aggregate(
                low=Count('id', filter=Q(risk_score__lte=40)),
                medium=Count('id', filter=Q(risk_score__gt=40, risk_score__lte=70)),
                high=Count('id', filter=Q(risk_score__gt=70))
            )

            metrics["risk_distribution"] = {
                "wallets": wallet_risk_dist
            }

            # Recent activity (bonus) - includes both Ethereum and Solana
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
