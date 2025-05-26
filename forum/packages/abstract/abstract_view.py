from services.utils.custom_pagination import (
    CustomParserPaginationMixin,
)
from services.utils.permission_handler import CustomPermissionHandler
from services.utils.exception_handler import ErrorHandlingMixin
from rest_framework import viewsets, mixins


class Helper(
    CustomParserPaginationMixin,
    CustomPermissionHandler,
    ErrorHandlingMixin,
):
    permission_classes = [CustomPermissionHandler]


class BaseForumView(
    Helper,
    CustomParserPaginationMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """base view for handling create list retrieve operations for Thread Model"""

    ...


class BaseReplyView(
    Helper,
    CustomParserPaginationMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
): ...


class BaseLikeView(
    Helper,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
): ...


class BaseTransactionDip(
    Helper,
    CustomParserPaginationMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
): ...


class BaseDipStatusUpdate(Helper, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    http_method_names = ["patch"]


class BaseVoters(
    Helper, CustomParserPaginationMixin, mixins.ListModelMixin, viewsets.GenericViewSet
): ...
