from rest_framework import mixins, viewsets
from services.utils.custom_pagination import (
    CustomParserPaginationMixin,
    CustomPagination,
)
from services.utils.permission_handler import CustomPermissionHandler

from services.utils.exception_handler import ErrorHandlingMixin

################### HELPER CLASSES ###################


class ListRetrieveView(mixins.ListModelMixin, mixins.RetrieveModelMixin): ...


class Helper(
    CustomParserPaginationMixin,
    CustomPermissionHandler,
    ErrorHandlingMixin,
):
    permission_classes = [CustomPermissionHandler]


#################### BASE CLASSES ###################


class BaseDaoView(
    Helper,
    ListRetrieveView,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """base view for authenticated dao operations. combines authentication parsers ,pagination, actions and error handling"""

    ...


class PublicBaseDaoView(
    Helper,
    ListRetrieveView,
    viewsets.GenericViewSet,
):
    """combines public access , parsers ,pagination, actions and error handling"""

    ...
