from django.db import models

class ContractAnalysis(models.Model):
    contract_address = models.CharField(max_length=42, db_index=True)
    detected_functions = models.JSONField(default=list)
    risk_flags = models.JSONField(default=list)
    risk_score = models.IntegerField(default=0)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Contract {self.contract_address} - Score: {self.risk_score}"
