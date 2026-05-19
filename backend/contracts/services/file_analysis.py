import logging
from .analysis import ContractAnalyzerService
from ai.services.gemma_service import GemmaService
from reports.services.pdf_generator import PDFGeneratorService

logger = logging.getLogger('contracts')


class FileAnalysisService:
    def __init__(self):
        self.analyzer = ContractAnalyzerService()
        self.ai_service = GemmaService()
        self.report_generator = PDFGeneratorService()

    def analyze_solidity_file(self, uploaded_file):
        try:
            source_code = uploaded_file.read().decode('utf-8')
        except Exception as e:
            logger.error("Failed to read uploaded Solidity file %s: %s", uploaded_file.name, e)
            return {"success": False, "error": f"Failed to read file: {str(e)}"}

        placeholder_address = f"file://{uploaded_file.name}"

        analysis_result = self.analyzer.run_analysis_on_source(
            address=placeholder_address,
            source_code=source_code,
            abi_string=None,
            metadata={"filename": uploaded_file.name}
        )

        if not analysis_result.get('success'):
            return analysis_result

        analysis_data = analysis_result['data']

        ai_explanation = self.ai_service.explain_contract({
            "source_code_preview": source_code[:1000],
            "risk_flags": analysis_data['risk_flags'],
            "risk_score": analysis_data['risk_score']
        })

        filename, filepath = self.report_generator.generate_report(
            "contract_file",
            analysis_data,
            ai_explanation
        )

        logger.info("Solidity file analysis complete for %s: score=%d", uploaded_file.name, analysis_data['risk_score'])

        return {
            "success": True,
            "data": {
                "risk_score": analysis_data['risk_score'],
                "detected_functions": analysis_data['detected_functions'],
                "risk_flags": analysis_data['risk_flags'],
                "ai_summary": ai_explanation,
                "report_url": f"/media/reports/{filename}"
            }
        }
