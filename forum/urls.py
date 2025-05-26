# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ThreadView,
    ThreadReplyView,
    DipView,
    DipSingleSyncronizationView,
    DipLikeView,
    DipReplyView,
    ReplyLikeView,
    ThreadLikeView,
    VoteSynchronizationView,
    VotingHistoryView,
)

app_name = "forum"

# Thread-related routes
thread_router = DefaultRouter()
thread_router.register(
    r"(?P<slug>[^/.]+)/threads", ThreadView, basename="thread-create"
)

thread_like_router = DefaultRouter()
thread_like_router.register(
    r"(?P<slug>[^/.]+)/threads/(?P<id>\d+)/like",
    ThreadLikeView,
    basename="thread-like",
)

thread_replies_router = DefaultRouter()
thread_replies_router.register(
    r"(?P<slug>[^/.]+)/threads/(?P<id>\d+)/replies",
    ThreadReplyView,
    basename="thread-reply",
)

thread_reply_like_router = DefaultRouter()
thread_reply_like_router.register(
    r"(?P<slug>[^/.]+)/threads/(?P<id>\d+)/replies/(?P<reply_id>\d+)/like",
    ReplyLikeView,
    basename="reply-like",
)

# Dip-related routes
dip_router = DefaultRouter()
dip_router.register(r"(?P<slug>[^/.]+)/dips", DipView, basename="dip-create")


dip_like_router = DefaultRouter()
dip_like_router.register(
    r"(?P<slug>[^/.]+)/dips/(?P<id>\d+)/like", DipLikeView, basename="dip-like"
)

dip_replies_router = DefaultRouter()
dip_replies_router.register(
    r"(?P<slug>[^/.]+)/dips/(?P<id>\d+)/replies",  # Fixed missing slash
    DipReplyView,
    basename="dip-reply",
)

dip_reply_like_router = DefaultRouter()
dip_reply_like_router.register(
    r"(?P<slug>[^/.]+)/dips/(?P<id>\d+)/replies/(?P<reply_id>\d+)/like",
    ReplyLikeView,
    basename="reply-like",
)

vote_router = DefaultRouter()
vote_router.register(
    r"refresh/dip/(?P<id>\d+)/vote",
    VoteSynchronizationView,
    basename="vote",
)


voting_history_router = DefaultRouter()

voting_history_router.register(
    r"(?P<slug>[^/.]+)/dips/(?P<id>\d+)/voters",
    VotingHistoryView,
    basename="voting-history",
)


urlpatterns = [
    path("", include(thread_router.urls)),
    path("", include(thread_like_router.urls)),
    path("", include(thread_replies_router.urls)),
    path("", include(thread_reply_like_router.urls)),
    path("", include(dip_router.urls)),
    path("", include(dip_like_router.urls)),
    path("", include(dip_replies_router.urls)),
    path("", include(dip_reply_like_router.urls)),
    path("", include(voting_history_router.urls)),
]
