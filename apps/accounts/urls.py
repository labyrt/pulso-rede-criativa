from django.urls import path

from .views import (
    BlockView,
    ConnectionsView,
    DiscoverCreatorsView,
    FollowView,
    LoginView,
    LogoutView,
    MeView,
    ProfileView,
    RegisterView,
    ResendVerificationView,
    TokenLoginView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/", TokenLoginView.as_view(), name="token"),
    path("me/", MeView.as_view(), name="me"),
    path("creators/", DiscoverCreatorsView.as_view(), name="creators"),
    path("profiles/<str:username>/", ProfileView.as_view(), name="profile"),
    path("profiles/<str:username>/follow/", FollowView.as_view(), name="follow"),
    path("profiles/<str:username>/block/", BlockView.as_view(), name="block"),
    path("profiles/<str:username>/<str:kind>/", ConnectionsView.as_view(), name="connections"),
]
