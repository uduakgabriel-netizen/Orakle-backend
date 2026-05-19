import os
from django.conf import settings
from rest_framework.test import APITestCase
from unittest.mock import patch
from reports.services.pdf_generator import PDFGeneratorService

class ReportGenerationTests(APITestCase):
    def test_pdf_generation_file_creation(self):
        service = PDFGeneratorService()
        analysis_data = {"risk_score": 85, "risk_flags": ["Test Flag"]}
        
        filename = service.generate_report("wallet", analysis_data, "Test AI summary")
        
        filepath = os.path.join(settings.BASE_DIR, 'media', 'reports', filename)
        self.assertTrue(os.path.exists(filepath))
        
        # Cleanup
        if os.path.exists(filepath):
            os.remove(filepath)
            
    def test_generate_report_view_invalid_type(self):
        response = self.client.post('/api/generate-report/', {"type": "invalid", "id": 1})
        self.assertEqual(response.status_code, 404) # Not found in urls? Let's assume view tests for validation
        # We can test validation via the view
        from reports.views import GenerateReportView
        from rest_framework.test import APIRequestFactory
        
        factory = APIRequestFactory()
        request = factory.post('/api/generate-report/', {"type": "invalid", "id": 1})
        view = GenerateReportView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['success'], False)
        self.assertEqual(response.data['message'], 'Invalid analysis type')
