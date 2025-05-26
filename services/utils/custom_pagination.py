from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

################### CUSTOM PAGINATION ###################


class CustomPagination(PageNumberPagination):
    page_size = 10

    def get_paginated_response(self, data):
        return Response(
            {
                "data": {
                    "count": self.page.paginator.count,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                    "results": data,
                }
            }
        )


class CustomParserPaginationMixin:
    """
    mixin for handling multiple parser types
    separates parser configs from view logic
    """

    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = CustomPagination
