from rest_framework.views import exception_handler


def pulso_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            "error": {
                "status": response.status_code,
                "message": "Não foi possível concluir esta ação.",
                "details": response.data,
            }
        }
    return response
