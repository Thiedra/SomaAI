from rest_framework.views import exception_handler

def custom_exception_handler(exc, context):
    """Return all errors as {"error": "<type>", "detail": "<message>"}."""
    response = exception_handler(exc, context)

    if response is not None:
        detail = response.data
        if isinstance(detail, dict) and "detail" in detail:
            detail = str(detail["detail"])
        elif isinstance(detail, list):
            detail = detail[0] if len(detail) == 1 else detail

        response.data = {"error": type(exc).__name__, "detail": detail}

    return response
