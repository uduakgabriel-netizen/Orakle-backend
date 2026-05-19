from django.db import models

class TransactionAnalysis(models.Model):
    tx_hash = models.CharField(max_length=66, db_index=True)
    chain = models.CharField(max_length=20, default='ethereum')
    parsed_data = models.JSONField(default=dict)
    interpretation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"TX {self.tx_hash}"
