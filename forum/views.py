from rest_framework.response import Response
from rest_framework import status
from django.contrib.contenttypes.models import ContentType
from django.db.models import F
from django.db import transaction
import logging
from drf_spectacular.utils import extend_schema
from django.db.models import When, Case, IntegerField, Sum
from .tasks import sync_dip_status, sync_votes_task

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# CUSTOM CLASSES
from .packages.abstract.abstract_view import (
    BaseVoters,
    BaseForumView,
    BaseReplyView,
    BaseLikeView,
    BaseTransactionDip,
    BaseTransactionDip,
    BaseDipStatusUpdate,
)
from services.utils.permission_handler import StakeRequiredPermissionHandler
from .serializers import (
    ThreadSerializer,
    ThreadDetailSerializer,
    DipSerializer,
    DipRefreshSerializer,
    DipDetailSerializer,
    ReplySerializer,
    LikeSerializer,
    VoteSerializer,
    VotingHistorySerializer,
    DipSingleRefreshSerializer,
    serializers,
)
from .models import Thread, Dip, DipStatus, Reply, Like, View, Vote


class BaseContentView(BaseForumView):

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        print(f"instance: {instance}")
        print(f"instance id: {instance.id}")
        print(f"user: {request.user}")
        content_type = ContentType.objects.get_for_model(instance)
        with transaction.atomic():
            # Only track views for authenticated users
            if request.user.is_authenticated:
                view, created = View.objects.update_or_create(
                    content_type=content_type,
                    object_id=instance.id,
                    user=request.user,
                )
                if created:
                    instance.views_count = F("views_count") + 1
                    instance.save()
                    instance.refresh_from_db()
            else:
                # For anonymous users, just increment the view count
                print(f"view not counted for anonymous user")
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        dao_slug = self.kwargs.get("slug")
        if not dao_slug:
            raise serializers.ValidationError("slug is required")

        serializer = self.get_serializer(
            data=request.data, context={"request": request, "slug": dao_slug}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


class BaseReplyContentView(BaseReplyView):
    """base view for replies to either Thread or Dip"""

    serializer_class = ReplySerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context_key = "thread_id" if self.model == Thread else "dip_id"
        context[context_key] = self.kwargs.get("id")
        return context

    def get_queryset(self):
        object_id = self.kwargs.get("id")
        return Reply.objects.filter(
            content_type=ContentType.objects.get_for_model(self.model),
            object_id=object_id,
        )

    def create(self, request, *args, **kwargs):
        object_id = self.kwargs.get("id")
        dao_slug = self.kwargs.get("slug")
        parent_obj = self.model.objects.get(id=object_id)
        if parent_obj.dao.slug != dao_slug:
            raise serializers.ValidationError("invalid dao slug for this content")
        serializer = self.get_serializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BaseLikeContentView(BaseLikeView):
    """base view for likes on any content type"""

    serializer_class = LikeSerializer
    model = None

    def get_content_type(self):
        return ContentType.objects.get_for_model(self.model)

    def get_object_id(self):
        object_id = self.kwargs.get("id")
        obj = self.model.objects.filter(id=object_id).first()

        if hasattr(obj, "dao") and obj.dao.slug != self.kwargs.get("slug"):
            raise serializers.ValidationError("slugs do not match")
        return object_id

    def create(self, request, *args, **kwargs):
        content_type = self.get_content_type()
        object_id = self.get_object_id()
        like = Like.objects.filter(
            user=request.user,
            content_type=content_type,
            object_id=object_id,
        ).first()
        if like:
            like.delete()
            return Response(
                {
                    "status": "unliked",
                    "msg": f"removed like from: {self.model.__name__} {object_id}",
                },
                status=status.HTTP_200_OK,
            )
        else:
            like = Like.objects.create(
                user=request.user,
                content_type=content_type,
                object_id=object_id,
            )
            print(f"created new like {like}")
            serializer = self.get_serializer(like)
            # QUESTION
            # serializer.is_valid(raise_exception=True)
            return Response({"status": "liked"}, status=status.HTTP_201_CREATED)


@extend_schema(tags=["thread"])
class ThreadView(BaseContentView):
    """
    thread view includes operations: list, retrieve, create for dip model
    """

    def get_serializer_class(self):
        return ThreadDetailSerializer if self.action == "retrieve" else ThreadSerializer

    def get_queryset(self):
        dao_slug = self.kwargs.get("slug")
        print(f"dao slug: {dao_slug}")

        thread = Thread.objects.filter(dao__slug=dao_slug).order_by('-created_at')
        return thread


@extend_schema(tags=["thread"])
class ThreadReplyView(BaseReplyContentView):
    model = Thread
    
    def get_queryset(self):
        """Override to order replies chronologically from oldest to newest"""
        queryset = super().get_queryset()
        return queryset.order_by('created_at')


@extend_schema(tags=["thread"])
class ThreadLikeView(BaseLikeContentView):
    model = Thread


@extend_schema(tags=["dynamic"])
class ReplyLikeView(BaseLikeContentView):
    model = Reply

    def get_object_id(self):
        reply_id = self.kwargs.get("reply_id")  # Get the reply_id from the URL
        obj = self.model.objects.filter(id=reply_id).first()
        if not obj:
            raise serializers.ValidationError(f"Reply with id {reply_id} not found")
        return reply_id


@extend_schema(tags=["dip"])
class DipReplyView(BaseReplyContentView):
    model = Dip
    
    def get_queryset(self):
        """Override to order replies chronologically from oldest to newest"""
        queryset = super().get_queryset()
        return queryset.order_by('created_at')


@extend_schema(tags=["dip"])
class DipLikeView(BaseLikeContentView):
    model = Dip

    def get_object_id(self):
        object_id = self.kwargs.get("id")
        obj = self.model.objects.filter(id=object_id).first()
        if hasattr(obj, "dao") and obj.dao.slug != self.kwargs.get("slug"):
            raise serializers.ValidationError("slugs do not match")
        return object_id


@extend_schema(tags=["dip"])
class DipView(BaseContentView):
    """
    dip view includes operations: list, retrieve, create for dip model
    Requires at least 1 token staked in the specific DAO to create a DIP
    """

    permission_classes = [StakeRequiredPermissionHandler]

    def create(self, request, *args, **kwargs):
        dao_slug = self.kwargs.get("slug")
        if not dao_slug:
            raise serializers.ValidationError("slug is required")

        # Check if user has enough tokens staked in this specific DAO
        min_stake_amount = 10**18  # 1 token with 18 decimals

        # Find the specific DAO
        try:
            from dao.models import Dao, Stake

            dao = Dao.objects.get(slug=dao_slug)
        except Dao.DoesNotExist:
            raise serializers.ValidationError(f"DAO with slug '{dao_slug}' not found")

        # Check user's stake in this specific DAO
        user_stake = Stake.objects.filter(user=request.user, dao=dao).first()

        if not user_stake or user_stake.amount < min_stake_amount:
            return Response(
                {
                    "error": f"You need at least 1 {dao.symbol} token staked in this DAO to create a DIP"
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Continue with the original method
        serializer = self.get_serializer(
            data=request.data, context={"request": request, "slug": dao_slug}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    def get_serializer_class(self):
        return DipDetailSerializer if self.action == "retrieve" else DipSerializer

    def get_queryset(self):
        dao_slug = self.kwargs.get("slug")
        status = self.request.query_params.get("status")
        queryset = Dip.objects.filter(dao__slug=dao_slug).exclude(
            status=DipStatus.DRAFT
        )
        if status:
            queryset = queryset.filter(status=status)

        return queryset.annotate(
            for_votes=Sum(
                Case(
                    When(votes__support=True, then=F("votes__voting_power")),
                    default=0,
                    output_field=IntegerField(),
                ),
            ),
            against_votes=Sum(
                Case(
                    When(votes__support=False, then=F("votes__voting_power")),
                    default=0,
                    output_field=IntegerField(),
                )
            ),
        ).order_by("-proposal_id")


@extend_schema(tags=["refresh"])
class DipSyncronizationView(BaseTransactionDip):
    """dip view for refreshing and synchronizing database records and on-chain proposals"""

    serializer_class = DipRefreshSerializer
    queryset = Dip.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["slug"] = self.kwargs.get("slug")
        return context

    def create(self, request, *args, **kwargs):

        serializer = self.serializer_class(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(
            {"message": "sync started"},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["refresh"])
class VoteSynchronizationView(BaseTransactionDip):
    serializer_class = VoteSerializer

    def get_queryset(self):
        return Vote.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["dip_id"] = self.kwargs.get("id")
        return context

    def create(self, request, *args, **kwargs):
        dip_id = self.kwargs.get("id")
        try:
            dip = Dip.objects.get(id=dip_id)
            if dip.status != DipStatus.ACTIVE:
                return Response(
                    {
                        "error": "cannot sync votes for inactive dip",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Dip.DoesNotExist:
            return Response(
                {"error": f"dip with id {dip_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        task = sync_votes_task.delay(dip_id)

        return Response(
            {
                "task_id": task.id,
                "dip_id": dip_id,
                "message": "vote sync task queued successfully",
            },
            status=status.HTTP_202_ACCEPTED,
        )


@extend_schema(tags=["dip"])
class VotingHistoryView(BaseVoters):
    serializer_class = VotingHistorySerializer

    def get_queryset(self):
        context = self.get_serializer_context()
        dip_id = context["id"]
        return Vote.objects.filter(dip_id=dip_id).all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["id"] = self.kwargs.get("id")

        return context


class DipSingleSyncronizationView(BaseDipStatusUpdate):
    serializer_class = DipSingleRefreshSerializer

    def get_queryset(self):
        return Dip.objects.filter(status=DipStatus.ACTIVE)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        task = sync_dip_status.delay(instance.id)

        return Response(
            {
                "proposal_id": instance.proposal_id,
                "task_id": task.id,
                "message": "Status update task queued successfully",
            },
            status=status.HTTP_202_ACCEPTED,
        )
