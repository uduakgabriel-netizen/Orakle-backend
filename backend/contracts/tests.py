import io
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from .models import ContractAnalysis

class ContractStage2Tests(APITestCase):
    def test_file_upload_validation_invalid_extension(self):
        file = SimpleUploadedFile("test.txt", b"dummy content", content_type="text/plain")
        response = self.client.post('/api/analyze-contract-file', {"contract_file": file}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])
        self.assertIn("Only .sol files are accepted", response.data['message'])

    def test_file_upload_missing_file(self):
        response = self.client.post('/api/analyze-contract-file', {}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])

    def test_contract_history_invalid_address(self):
        response = self.client.get('/api/contract-history/0x123')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])

    def test_contract_history_valid_address_empty(self):
        addr = "0x" + "1" * 40
        response = self.client.get(f'/api/contract-history/{addr}')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']['history']), 0)
