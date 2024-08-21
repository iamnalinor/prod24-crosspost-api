from pyrogram.errors import Unauthorized, NotAcceptable
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, (Unauthorized, NotAcceptable)):
        return Response(
            {"error": "telegram auth exception", "data": str(exc)},
            status=406
        )

    return response
