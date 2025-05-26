from rest_framework.exceptions import (
    AuthenticationFailed,
    PermissionDenied,
)
from rest_framework.permissions import (
    BasePermission,
    SAFE_METHODS,
)
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.urls import resolve
from logging_config import logger
from dao.models import Stake, Dao


class CustomPermissionHandler(BasePermission):
    # """
    # Unified permission handler for DAO and Forum operations:
    # - Public GET access for viewing DAOs and forum content
    # - JWT required for forum actions (posts, replies, likes)
    # - JWT + ownership required for DAO manipulations
    # """

    OWNER_REQUIRED_ENDPOINTS = [
        "dao-fetch",
        "dao-save",
    ]  # Removed refresh-status since it operates on Dip objects which use author instead of owner
    AUTH_REQUIRED_ENDPOINTS = [
        "thread-create",
        "dip-create",
        "thread-like",
        "dip-like",
        "thread-reply",
        "dip-reply",
        "reply-like",
        "refresh-status",  # Added here since it only needs authentication, not ownership check
    ]

    def authenticate(self, request):
        """Attempt authentication for all requests"""
        jwt_auth = JWTAuthentication()
        try:
            result = jwt_auth.authenticate(request)
            return result
        except Exception:
            raise

    def resolve_url(self, request):
        resolved = resolve(request.path_info)
        return resolved.url_name

    def has_permission(self, request, view):
        """Check permissions based on endpoint requirements"""
        url_path = self.resolve_url(request)
        if url_path == "refresh-stake":
            return True

        # If endpoint requires authentication
        if url_path in self.AUTH_REQUIRED_ENDPOINTS + self.OWNER_REQUIRED_ENDPOINTS:
            auth_result = self.authenticate(request)
            if not auth_result:
                return False
            user, token = auth_result
            request.user = user
            return True

        # For non-auth endpoints, allow safe methods
        if request.method in SAFE_METHODS:
            auth_result = self.authenticate(request)
            return True

        # For other methods on non-auth endpoints, require authentication
        auth_result = self.authenticate(request)
        if not auth_result:
            raise AuthenticationFailed(
                "authentication credentials were not provided",
            )
        user, token = auth_result
        request.user = user
        return True

    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        url_path = self.resolve_url(request)
        if url_path == "refresh-stake":
            return True

        # Owner required endpoints need ownership check
        if url_path in self.OWNER_REQUIRED_ENDPOINTS:
            return bool(request and request.user == obj.owner)

        # Auth required endpoints need authentication check
        if url_path in self.AUTH_REQUIRED_ENDPOINTS:
            return bool(request.user and request.user.is_authenticated)

        # For other endpoints, allow safe methods
        if request.method in SAFE_METHODS:
            auth_result = self.authenticate(request)
            logger.debug(f"request: {request}\nauth result: {auth_result}")
            return True

        # For non-safe methods, require authentication
        return bool(request.user and request.user.is_authenticated)

    def authenticate_header(self, request):
        """Return Bearer auth header for all requests to ensure Swagger includes auth"""
        return 'Bearer realm="api"'


class StakeRequiredPermissionHandler(CustomPermissionHandler):
    """
    Permission handler that extends CustomPermissionHandler to also check
    if the user has enough tokens staked in the specific DAO when creating a DIP.
    """

    def has_permission(self, request, view):
        # First check the parent permissions
        if not super().has_permission(request, view):
            return False

        # Only check stake for DIP creation with POST method
        url_path = self.resolve_url(request)
        if url_path == "dip-create" and request.method == "POST":
            # Get the DAO slug from the URL
            dao_slug = request.resolver_match.kwargs.get("slug")
            if not dao_slug:
                return False

            # Check if user has enough tokens staked in this specific DAO
            min_stake_amount = 10**18  # 1 token with 18 decimals

            # Find the specific DAO
            try:
                dao = Dao.objects.get(slug=dao_slug)
            except Dao.DoesNotExist:
                raise PermissionDenied(
                    {"error": f"DAO with slug '{dao_slug}' not found"}
                )

            # Check user's stake in this specific DAO
            user_stake = Stake.objects.filter(user=request.user, dao=dao).first()

            if not user_stake or user_stake.amount < min_stake_amount:
                raise PermissionDenied(
                    {
                        "error": f"You need at least 1 {dao.symbol} token staked in this DAO to create a DIP"
                    }
                )

        return True
