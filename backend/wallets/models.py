from django.db import models

class WalletAnalysis(models.Model):
    wallet_address = models.CharField(max_length=42, db_index=True)
    chain = models.CharField(max_length=20, default='ethereum')
    risk_score = models.IntegerField(default=0)
    signals = models.JSONField(default=list)
    raw_metrics = models.JSONField(default=dict)
    response_payload = models.JSONField(default=dict, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Wallet {self.wallet_address} - Score: {self.risk_score}"
