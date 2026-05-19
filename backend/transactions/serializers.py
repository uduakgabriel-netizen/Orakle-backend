from rest_framework import serializers
from .models import TransactionAnalysis

class TransactionAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionAnalysis
        fields = '__all__'
