from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.shortcuts import get_object_or_404

# CUSTOM MODULES
from .models import Dao, Stake, Presale, Contract, PresaleTransaction
from .serializers import (
    DaoInitialSerializer,
    StakeSerializer,
    DaoCompleteSerializer,
    DaoActiveSerializer,
    PresaleSerializer,
    PresaleTransactionSerializer,
)
from .packages.abstract.abstract_views import (
    BaseDaoView,
    PublicBaseDaoView,
)
from .packages.services.presale_service import PresaleService
from django.db.models import When, Case, Sum, Count, F
from logging_config import logger
from services.utils.custom_pagination import CustomPagination

######################## VIEWS ########################


# DAO CREATION/DEPLOYMENT


@extend_schema(tags=["dao"])
class DaoInitialView(BaseDaoView):
    """view for managing user's DAOs
    supports: list, retrieve, create for authenticated users
    """

    serializer_class = DaoInitialSerializer

    def get_queryset(self):
        return Dao.objects.filter(owner=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        context["network"] = self.request.data.get("network")
        return context


@extend_schema(tags=["refresh"])
class StakeView(BaseDaoView):
    serializer_class = StakeSerializer

    def paginate_queryset(self, queryset):
        dao_id = self.request.GET.get("id")
        slug = self.request.GET.get("slug")

        if dao_id or slug:
            return None
        return super().paginate_queryset(queryset)

    def get_queryset(self):
        dao_id = self.request.GET.get("id")
        slug = self.request.GET.get("slug")

        queryset = Stake.objects.all()
        if dao_id:
            queryset = queryset.filter(dao__id=dao_id)
        elif slug:
            queryset = queryset.filter(dao__slug=slug)
        return queryset.order_by("-amount")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.method == "POST":
            # For POST: Get params from request body
            context["dao_id"] = self.request.data.get("id")
            context["slug"] = self.request.data.get("dao_slug")
        else:
            # For GET: Get params from query string
            context["dao_id"] = self.request.GET.get("id")
            context["slug"] = self.request.GET.get("slug")
        context["user"] = self.request.user
        return context

    @extend_schema(
        parameters=[
            OpenApiParameter(name="id", type=int, description="filter by id"),
            OpenApiParameter(name="slug", type=str, description="filter by slug"),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


@extend_schema(tags=["dao"])
class DaoCompleteView(BaseDaoView):
    serializer_class = DaoCompleteSerializer
    queryset = Dao.objects.all()

    def get_object(self):
        dao_id = self.request.data.get("id")
        return Dao.objects.get(id=dao_id)
        
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


# RETRIEVE ACTIVE DAOS REQUIRES NO AUTH
@extend_schema(tags=["dao"])
class ActiveDaosView(PublicBaseDaoView):
    """
    view for public access to active DAOs
    supports: list, retrieve for all users
    """

    serializer_class = DaoActiveSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Dao.objects.filter(is_active=True).annotate(
            staker_count=Count("dao_stakers"),
            total_staked=Sum("dao_stakers__amount"),
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


@extend_schema(tags=["presale"])
class PresaleView(PublicBaseDaoView):
    """
    View for accessing presale information
    Supports: list, retrieve for all users
    """

    serializer_class = PresaleSerializer

    def get_queryset(self):
        slug = self.kwargs.get("slug")
        if slug:
            return Presale.objects.filter(dao__slug=slug).order_by("-created_at")
        return Presale.objects.all().order_by("-created_at")

    def get_object(self):
        # If we're using the retrieve action, use the pk from kwargs
        if self.action == "retrieve":
            return get_object_or_404(Presale, id=self.kwargs.get("pk"))
        return super().get_object()
        
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="slug", type=str, description="Filter presales by DAO slug"
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        parameters=[
            OpenApiParameter(name="pk", type=int, description="Presale ID"),
        ],
        description="Retrieve a single presale by ID",
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


@extend_schema(tags=["refresh"])
class PresaleRefreshView(BaseDaoView):
    """
    View for refreshing presale state from the blockchain
    """

    def get_serializer_class(self):
        return PresaleSerializer

    def get_object(self):
        presale_id = self.kwargs.get("id")
        return get_object_or_404(Presale, id=presale_id)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context
        
    def update(self, request, *args, **kwargs):
        presale = self.get_object()

        # Get the contract for the presale's DAO
        contract = get_object_or_404(Contract, dao_id=presale.dao_id)

        # Update the presale state
        presale_service = PresaleService(
            presale_contract=presale.presale_contract, network=contract.network
        )
        updated_presale = presale_service.update_presale_state(presale)

        if not updated_presale:
            return Response(
                {"error": "Failed to update presale state"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Fetch and process events
        presale_service.fetch_presale_events(updated_presale)

        serializer = self.get_serializer(updated_presale)
        return Response(serializer.data)


@extend_schema(tags=["presale"])
class PresaleTransactionsView(PublicBaseDaoView):
    """
    View for accessing presale transaction history
    Supports: list for all users with pagination
    """

    serializer_class = PresaleTransactionSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        presale_id = self.kwargs.get("id")
        return PresaleTransaction.objects.filter(presale_id=presale_id).order_by(
            "-timestamp"
        )
        
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="page", type=int, description="Page number for pagination"
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                description="Number of items per page (max 10)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
