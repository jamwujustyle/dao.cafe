from django.urls import path

from .views import DaoInitialView, DaoCompleteView, ActiveDaosView, PresaleView, StakeView, PresaleRefreshView, PresaleTransactionsView

app_name = "dao"

urlpatterns = [
    path("", ActiveDaosView.as_view({"get": "list"}), name="daos-list"),
    path("fetch/", DaoInitialView.as_view({"post": "create"}), name="dao-fetch"),
    path("save/", DaoCompleteView.as_view({"patch": "update"}), name="dao-save"),
    path(
        "<slug:slug>/info/",
        ActiveDaosView.as_view({"get": "retrieve"}),
        name="daos-retrieve",
    ),
    path(
        "stakes/",
        StakeView.as_view({"get": "list", "post": "create"}),
        name="stakes-list-create",
    ),
    path(
        "presales/",
        PresaleView.as_view({"get": "list"}),
        name="presales-list",
    ),
    path(
        "<slug:slug>/presales/",
        PresaleView.as_view({"get": "list"}),
        name="dao-presales-list",
    ),
    path(
        "presales/<int:pk>/",
        PresaleView.as_view({"get": "retrieve"}),
        name="presale-detail",
    ),
    path(
        "presales/<int:id>/refresh/",
        PresaleRefreshView.as_view({"patch": "update"}),
        name="presale-refresh",
    ),
    path(
        "presales/<int:id>/transactions/",
        PresaleTransactionsView.as_view({"get": "list"}),
        name="presale-transactions",
    ),
]
