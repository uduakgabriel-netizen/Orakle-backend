from rest_framework.response import Response

def standardized_response(success=True, data=None, message="", status_code=200):
    return Response({
        "success": success,
        "data": data or {},
        "message": message
    }, status=status_code)
