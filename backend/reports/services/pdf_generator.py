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

    def generate_report(self, analysis_type, analysis_data, ai_explanation):
        """
        Generate a PDF report and return (filename, filepath) tuple.
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
                f.write(ai_explanation + "\n")
            logger.info("Generated TXT report (fpdf2 unavailable): %s", filename)
            return filename, filepath

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

        # AI Intelligence Summary & Recommendations
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'AI Intelligence Summary & Recommendations', new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('Helvetica', '', 11)

        ai_text_clean = ai_explanation.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, ai_text_clean, new_x="LMARGIN", new_y="NEXT")

        pdf.output(filepath)
        logger.info("Generated PDF report: %s", filename)
        return filename, filepath
