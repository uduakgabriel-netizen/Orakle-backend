from rest_framework import serializers
from .models import WalletAnalysis

class WalletAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletAnalysis
        fields = '__all__'
