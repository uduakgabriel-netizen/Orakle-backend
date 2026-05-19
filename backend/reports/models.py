from django.db import models

class Report(models.Model):
    # Flexible relation to different analysis types
    analysis_type = models.CharField(max_length=50) # 'wallet', 'contract', 'transaction'
    related_analysis_id = models.IntegerField()
    pdf_file = models.FileField(upload_to='reports/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report {self.id} for {self.analysis_type} {self.related_analysis_id}"
