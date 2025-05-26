from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
    APIException,
    MethodNotAllowed,
    ParseError,
    AuthenticationFailed,
    NotAcceptable,
    UnsupportedMediaType,
    NotAuthenticated,
    Throttled,
)
from django.http import Http404
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.utils import IntegrityError
from logging_config import logger
from rest_framework.response import Response
from rest_framework import status, serializers
import redis


class ErrorHandlingMixin:
    """
    mixin for consistent error handling across views
    """

    def handle_exception(self, ex):
        if isinstance(ex, (NotFound, Http404, ObjectDoesNotExist)):
            return Response(
                {"error": f"resource not found: {str(ex)}"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if isinstance(ex, MultipleObjectsReturned):
            return Response(
                {"error": f"multiple objects returned: {str(ex)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if isinstance(ex, PermissionDenied):
            return Response(
                {"error": f"permission denied: {str(ex)}"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if isinstance(ex, MethodNotAllowed):
            return Response(
                {"error": f"method not allowed: {str(ex)}"},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )

        if isinstance(ex, serializers.ValidationError):
            return Response({"error": ex.detail}, status=status.HTTP_400_BAD_REQUEST)

        if isinstance(ex, ParseError):
            return Response(
                {"error": f"malformed request: {str(ex)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if isinstance(ex, (AuthenticationFailed, NotAuthenticated)):
            return Response(
                {"error": ex.detail},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if isinstance(ex, NotAcceptable):
            return Response(
                {"error": f"could not satisfy the request Accept header: {str(ex)}"},
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        if isinstance(ex, UnsupportedMediaType):
            return Response(
                {"error": f"unsupported media type in request: {str(ex)}"},
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )
        if isinstance(ex, IntegrityError):
            return Response(
                {"error": f"database integrity error: {str(ex)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        if isinstance(ex, redis.exceptions.ConnectionError):
            return Response(
                {"error": f"redis connection error: {str(ex)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if isinstance(ex, Throttled):
            return Response(
                {"error": f"request throttled. try again in {ex.wait} seconds."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            
        if isinstance(ex, (TypeError, ValueError)):
            return Response(
                {"error": f"invalid input: {str(ex)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if isinstance(ex, APIException):
            return Response(
                {"error": f"operation failed. reason: {str(ex)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        # capture dynamically
        status_code = getattr(ex, "status_code", None)
        if (
            isinstance(ex, Exception)
            and isinstance(ex.args, tuple)
            and len(ex.args) == 2
        ):
            message, code = ex.args
            if isinstance(code, int):
                return Response({"error": str(message)}, status=code)

        return Response(
            {"error": f"operation failed. reason: {str(ex)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
