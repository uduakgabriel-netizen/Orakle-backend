from django.db import models

class SolanaWalletAnalysis(models.Model):
    wallet_address = models.CharField(max_length=44, db_index=True) # Solana addresses are up to 44 chars
    risk_score = models.IntegerField(default=0)
    signals = models.JSONField(default=list)
    metrics = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Solana Wallet {self.wallet_address} - {self.risk_score}"

class SolanaTransactionAnalysis(models.Model):
    signature = models.CharField(max_length=88, db_index=True) # Solana signatures are longer
    interpretation = models.TextField()
    raw_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Solana TX {self.signature}"
