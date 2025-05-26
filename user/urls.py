from django.urls import path
from user import views

app_name = "user"

urlpatterns = [
    path(
        "profile/",
        views.UserApiView.as_view(
            {
                "get": "user_profile",
                "patch": "user_patch",
            }
        ),
        name="profile",
    ),
]
