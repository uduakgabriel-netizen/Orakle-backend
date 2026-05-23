from rest_framework.response import Response
from django.utils import timezone

def standardized_response(success=True, data=None, message="", status_code=200):
    return Response({
        "success": success,
        "data": data or {},
        "message": message,
        "generated_at": timezone.now().isoformat()
    }, status=status_code)
