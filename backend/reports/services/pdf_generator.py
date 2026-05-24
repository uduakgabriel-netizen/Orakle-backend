import os
import logging
from django.conf import settings
from datetime import datetime

logger = logging.getLogger('reports')

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None
    logger.warning("fpdf2 not installed. PDF reports will fall back to TXT format.")


class PDFGeneratorService:
    def __init__(self):
        self.media_path = os.path.join(settings.BASE_DIR, 'media', 'reports')
        if not os.path.exists(self.media_path):
            os.makedirs(self.media_path)

    def generate_report(self, analysis_data: dict, ai_explanation: dict, analysis_type: str = "contract") -> str:
        """
        Generate a PDF report and return the filepath.
        Falls back to TXT if fpdf2 is unavailable.
        """
        filename = f"report_{analysis_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.media_path, filename)

        if FPDF is None:
            filename = filename.replace('.pdf', '.txt')
            filepath = filepath.replace('.pdf', '.txt')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"ORAKLE INTELLIGENCE REPORT\n")
                f.write(f"Type: {analysis_type}\n")
                f.write(f"Date: {datetime.now()}\n\n")
                f.write("--- DETERMINISTIC ANALYSIS ---\n")
                f.write(str(analysis_data) + "\n\n")
                f.write("--- AI REASONING ---\n")
                if isinstance(ai_explanation, dict):
                    f.write(f"Threat Assessment: {ai_explanation.get('threat_assessment', 'N/A')}\n")
                    f.write(f"Summary: {ai_explanation.get('summary', '')}\n")
                    f.write("Key Findings:\n")
                    for find in ai_explanation.get('key_findings', []):
                        f.write(f"- {find}\n")
                    f.write("Recommendations:\n")
                    for rec in ai_explanation.get('recommendations', []):
                        f.write(f"- {rec}\n")
                else:
                    f.write(str(ai_explanation) + "\n")
            logger.info("Generated TXT report (fpdf2 unavailable): %s", filename)
            return filepath

        class ReportPDF(FPDF):
            def header(self):
                self.set_font('Helvetica', 'B', 18)
                self.cell(0, 10, 'ORAKLE INTELLIGENCE REPORT', align='C', new_x="LMARGIN", new_y="NEXT")
                self.set_font('Helvetica', 'I', 10)
                self.set_text_color(100, 100, 100)
                self.cell(0, 8, f'Type: {analysis_type.upper().replace("_", " ")} | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', align='C', new_x="LMARGIN", new_y="NEXT")
                self.ln(5)

            def footer(self):
                self.set_y(-15)
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(128, 128, 128)
                self.cell(0, 10, f'Page {self.page_no()}', align='C')

        pdf = ReportPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Executive Summary
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, 'Executive Summary', new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('Helvetica', '', 11)
        pdf.multi_cell(0, 6, "This report provides an automated deterministic and AI-assisted intelligence analysis of the requested target. Findings are based on on-chain data and pattern recognition.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        # Risk Score
        risk_score = analysis_data.get('risk_score', 'N/A')
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'Risk Score', new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('Helvetica', 'B', 12)

        if isinstance(risk_score, (int, float)):
            if risk_score > 70:
                pdf.set_text_color(220, 53, 69)
            elif risk_score > 40:
                pdf.set_text_color(255, 193, 7)
            else:
                pdf.set_text_color(40, 167, 69)
        else:
            pdf.set_text_color(0, 0, 0)

        pdf.cell(0, 8, f'{risk_score} / 100', new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)

        # Detected Signals / Risk Flags
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'Detected Signals', new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('Helvetica', '', 11)

        signals = analysis_data.get('risk_flags', analysis_data.get('signals', []))
        if signals:
            for signal in signals:
                pdf.multi_cell(0, 6, f"- {signal}", new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.cell(0, 6, "No specific signals detected.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        # Metrics & Additional Data
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'Metrics & Additional Data', new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('Helvetica', '', 11)

        has_metrics = False
        for k, v in analysis_data.items():
            if k not in ['risk_score', 'risk_flags', 'signals']:
                pdf.multi_cell(0, 6, f"{str(k).replace('_', ' ').capitalize()}: {v}", new_x="LMARGIN", new_y="NEXT")
                has_metrics = True

        if not has_metrics:
            pdf.cell(0, 6, "No additional metrics available.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        # AI Intelligence Summary
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'AI Intelligence Summary', new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('Helvetica', '', 11)

        if isinstance(ai_explanation, dict):
            summary = ai_explanation.get('summary', '')
            threat = ai_explanation.get('threat_assessment', 'N/A')
            findings = ai_explanation.get('key_findings', [])
            recommendations = ai_explanation.get('recommendations', [])

            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(0, 8, f"Threat Assessment: {threat}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font('Helvetica', '', 11)
            
            summary_clean = summary.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 6, summary_clean, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

            if findings:
                pdf.set_font('Helvetica', 'B', 12)
                pdf.cell(0, 8, "Key Findings", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font('Helvetica', '', 11)
                for f in findings:
                    f_clean = f.encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 6, f"- {f_clean}", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(3)

            if recommendations:
                pdf.set_font('Helvetica', 'B', 12)
                pdf.cell(0, 8, "Recommendations", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font('Helvetica', '', 11)
                for r in recommendations:
                    r_clean = r.encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 6, f"- {r_clean}", new_x="LMARGIN", new_y="NEXT")
        else:
            ai_text_clean = str(ai_explanation).encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 6, ai_text_clean, new_x="LMARGIN", new_y="NEXT")

        pdf.output(filepath)
        logger.info("Generated PDF report: %s", filename)
        return filepath
