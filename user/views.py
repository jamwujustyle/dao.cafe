from rest_framework import (
    viewsets,
    mixins,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import action
from user.serializers import (
    UserSerializer,
    UserDetailSerializer,
)
from core.models import User
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from drf_spectacular.utils import extend_schema
from services.utils.exception_handler import ErrorHandlingMixin


class BaseUserView(
    ErrorHandlingMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        """retrieves objects belonging to the authenticated user"""
        return User.objects.filter(eth_address=self.request.user.eth_address)


class UserApiView(BaseUserView):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "eth_address"
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(responses=UserDetailSerializer)
    @action(detail=False, methods=["get"], url_path="profile")
    def user_profile(self, request):
        user_instance = request.user

        serializer = UserDetailSerializer(user_instance, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    ####Patch endpoint for user####
    @action(detail=False, methods=["patch"], url_path="patch")
    def user_patch(self, request):
        """partially updates the user (nickname, email)"""
        serializer = self.get_serializer(
            instance=request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)
