from rest_framework import serializers
from .models import ContractAnalysis

class ContractAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractAnalysis
        fields = '__all__'
