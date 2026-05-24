import re
import logging
from .analysis import ContractAnalyzerService
from reports.services.pdf_generator import PDFGeneratorService

logger = logging.getLogger('contracts')


class FileAnalysisService:
    def __init__(self):
        self.analyzer = ContractAnalyzerService()
        self.report_generator = PDFGeneratorService()

    def analyze_solidity_file(self, uploaded_file):
        try:
            source_code = uploaded_file.read().decode('utf-8')
        except Exception as e:
            logger.error("Failed to read uploaded Solidity file %s: %s", uploaded_file.name, e)
            return {"success": False, "error": f"Failed to read file: {str(e)}"}

        placeholder_address = f"file://{uploaded_file.name}"

        # Extract pragma version and contract name using regex
        pragma_match = re.search(r"pragma\s+solidity\s+([^;]+);", source_code)
        pragma_version = pragma_match.group(1).strip() if pragma_match else "unknown"

        contract_match = re.search(r"contract\s+(\w+)", source_code)
        contract_name = contract_match.group(1).strip() if contract_match else "unknown"

        metadata = {
            "name": contract_name,
            "compiler": pragma_version,
            "filename": uploaded_file.name
        }

        # Analyze using analyzer service, passing type="contract_file"
        analysis_result = self.analyzer.run_analysis_on_source(
            address=placeholder_address,
            source_code=source_code,
            abi_string=None,
            metadata=metadata,
            type="contract_file"
        )

        if not analysis_result.get('success'):
            return analysis_result

        analysis_data = analysis_result['data']
        analysis_id = analysis_data.get('id')

        # Generate PDF report using the universal analysis shape directly
        try:
            pdf_path = self.report_generator.generate_report(
                analysis_data=analysis_data,
                ai_explanation=analysis_data.get('ai_summary')
            )
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            pdf_path = None  # Don't break the whole request

        if pdf_path:
            try:
                # Create a Report object in the database so it persists in history
                from reports.models import Report
                from django.core.files import File
                import os
                
                filename = os.path.basename(pdf_path)
                
                report = Report.objects.create(
                    analysis_type='contract',
                    related_analysis_id=analysis_id
                )
                
                with open(pdf_path, 'rb') as f:
                    report.pdf_file.save(filename, File(f), save=True)

                analysis_data["report_url"] = report.pdf_file.url
                analysis_data["report_available"] = True
            except Exception as e:
                logger.error(f"Failed to save report PDF: {e}")

        logger.info("Solidity file analysis complete for %s: score=%d", uploaded_file.name, analysis_data['risk_score'])

        return {
            "success": True,
            "data": analysis_data
        }
