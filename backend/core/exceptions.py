from rest_framework.views import exception_handler
from .utils import standardized_response

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        return standardized_response(
            success=False,
            message=str(exc),
            status_code=response.status_code
        )

    return standardized_response(
        success=False,
        message="An unexpected error occurred.",
        status_code=500
    )
