import logging
from django.core.files import File
from rest_framework.views import APIView
from .services.pdf_generator import PDFGeneratorService
from .models import Report
from wallets.models import WalletAnalysis
from contracts.models import ContractAnalysis
from transactions.models import TransactionAnalysis
from solana.models import SolanaWalletAnalysis, SolanaTransactionAnalysis
from ai.services.gemma_service import GemmaService
from core.utils import standardized_response

logger = logging.getLogger('reports')


class GenerateReportView(APIView):
    def post(self, request):
        analysis_type = request.data.get('type')
        analysis_id = request.data.get('id')

        if not analysis_type or not analysis_id:
            return standardized_response(success=False, message="type and id are required", status_code=400)

        if analysis_type not in ['wallet', 'contract', 'transaction', 'solana_wallet', 'solana_transaction']:
            return standardized_response(success=False, message="Invalid analysis type", status_code=400)

        try:
            if analysis_type == 'wallet':
                obj = WalletAnalysis.objects.get(id=analysis_id)
                analysis_data = {
                    "address": obj.wallet_address,
                    "risk_score": obj.risk_score,
                    "signals": obj.signals,
                    "metrics": obj.raw_metrics
                }
            elif analysis_type == 'contract':
                obj = ContractAnalysis.objects.get(id=analysis_id)
                analysis_data = {
                    "address": obj.contract_address,
                    "risk_score": obj.risk_score,
                    "risk_flags": obj.risk_flags,
                    "detected_functions": obj.detected_functions
                }
            elif analysis_type == 'transaction':
                obj = TransactionAnalysis.objects.get(id=analysis_id)
                # If interpretation is already a dict, we use it directly
                if isinstance(obj.interpretation, dict):
                    ai_explanation = obj.interpretation
                    analysis_data = {"hash": obj.tx_hash, "parsed_data_preview": str(obj.parsed_data)[:500]}
                else:
                    analysis_data = {"hash": obj.tx_hash, "interpretation": obj.interpretation}
            elif analysis_type == 'solana_wallet':
                obj = SolanaWalletAnalysis.objects.get(id=analysis_id)
                analysis_data = {
                    "address": obj.wallet_address,
                    "risk_score": obj.risk_score,
                    "signals": obj.signals,
                    "metrics": obj.metrics
                }
            elif analysis_type == 'solana_transaction':
                obj = SolanaTransactionAnalysis.objects.get(id=analysis_id)
                analysis_data = {
                    "signature": obj.signature,
                    "interpretation": obj.interpretation
                }
        except (WalletAnalysis.DoesNotExist, ContractAnalysis.DoesNotExist, TransactionAnalysis.DoesNotExist, SolanaWalletAnalysis.DoesNotExist, SolanaTransactionAnalysis.DoesNotExist):
            return standardized_response(success=False, message="Analysis object not found", status_code=404)

        try:
            # Check if we already have the ai_explanation from transaction logic
            if 'ai_explanation' not in locals():
                ai_service = GemmaService()
                if analysis_type == 'wallet' or analysis_type == 'solana_wallet':
                    ai_explanation = ai_service.explain_wallet(analysis_data)
                elif analysis_type == 'contract':
                    ai_explanation = ai_service.explain_contract(analysis_data)
                else:
                    ai_explanation = ai_service.translate_transaction(analysis_data)

            generator = PDFGeneratorService()
            filepath = generator.generate_report(
                analysis_data=analysis_data,
                ai_explanation=ai_explanation,
                analysis_type=analysis_type
            )
            import os
            filename = os.path.basename(filepath)

            report = Report.objects.create(
                analysis_type=analysis_type,
                related_analysis_id=analysis_id,
            )

            with open(filepath, 'rb') as pdf_file:
                report.pdf_file.save(filename, File(pdf_file), save=True)

            logger.info("Report %d generated for %s #%s: %s", report.id, analysis_type, analysis_id, filename)

            # Return absolute URL to avoid 404 issues on frontend
            pdf_url = request.build_absolute_uri(report.pdf_file.url)
            
            return standardized_response(
                data={
                    "report_id": report.id,
                    "pdf_url": pdf_url
                },
                message="Report generated successfully",
                status_code=201
            )
        except Exception as e:
            logger.error("Report generation failed for %s #%s: %s", analysis_type, analysis_id, e)
            return standardized_response(success=False, message="An internal error occurred during report generation.", status_code=500)
