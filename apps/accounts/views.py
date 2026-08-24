from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.social.models import Notification
from apps.webapp.throttles import AuthRateThrottle

from .media_serializers import ProfileMediaUpdateSerializer
from .models import Block, Follow, Profile, User
from .serializers import ProfileUpdateSerializer, PublicProfileSerializer, RegisterSerializer, UserSummarySerializer


def blocked_user_ids(user):
    blocked = Block.objects.filter(blocker=user).values_list("blocked_id", flat=True)
    blocked_by = Block.objects.filter(blocked=user).values_list("blocker_id", flat=True)
    return blocked, blocked_by


def visible_people_for(user):
    blocked, blocked_by = blocked_user_ids(user)
    return (
        User.objects.select_related("profile")
        .filter(is_active=True, profile__is_hidden=False)
        .exclude(pk=user.pk)
        .exclude(pk__in=blocked)
        .exclude(pk__in=blocked_by)
    )


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        user = User.objects.get(username=response.data["username"])
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response(PublicProfileSerializer(user.profile, context={"request": request}).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        identifier = request.data.get("identifier", "").strip()
        password = request.data.get("password", "")
        if "@" in identifier:
            username = User.objects.filter(email__iexact=identifier).values_list("username", flat=True).first()
        else:
            username = identifier.lower()
        user = authenticate(request, username=username, password=password)
        if not user or not user.is_active:
            return Response({"detail": "Credenciais inválidas."}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)
        return Response(PublicProfileSerializer(user.profile, context={"request": request}).data)


class TokenLoginView(APIView):
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        token, _ = Token.objects.get_or_create(user=request.user)
        return Response({"token": token.key})


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response(PublicProfileSerializer(request.user.profile, context={"request": request}).data)

    def patch(self, request):
        has_media = any(field in request.FILES for field in ("avatar_upload", "cover_upload"))
        serializer_class = ProfileMediaUpdateSerializer if has_media else ProfileUpdateSerializer
        serializer = serializer_class(request.user.profile, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(PublicProfileSerializer(request.user.profile, context={"request": request}).data)


class ProfileView(generics.RetrieveAPIView):
    serializer_class = PublicProfileSerializer
    lookup_field = "user__username"
    lookup_url_kwarg = "username"

    def get_queryset(self):
        profiles = Profile.objects.select_related("user").filter(user__is_active=True)
        if self.request.user.is_authenticated:
            return profiles.filter(Q(is_hidden=False) | Q(user=self.request.user))
        return profiles.filter(is_hidden=False)


class DiscoverCreatorsView(generics.ListAPIView):
    serializer_class = UserSummarySerializer
    search_fields = ["username", "profile__display_name", "profile__specialty", "profile__bio"]

    def get_queryset(self):
        return visible_people_for(self.request.user).order_by("?")


class FollowView(APIView):
    def post(self, request, username):
        target = generics.get_object_or_404(User.objects.select_related("profile"), username=username, is_active=True, profile__is_hidden=False)
        if target == request.user:
            return Response({"detail": "Você não pode seguir a si mesma."}, status=status.HTTP_400_BAD_REQUEST)
        if Block.objects.filter(Q(blocker=request.user, blocked=target) | Q(blocker=target, blocked=request.user)).exists():
            return Response({"detail": "Esta conexão não está disponível."}, status=status.HTTP_403_FORBIDDEN)
        follow, created = Follow.objects.get_or_create(follower=request.user, following=target)
        if created:
            Notification.objects.create(recipient=target, actor=request.user, kind=Notification.Kind.FOLLOW)
        else:
            follow.delete()
        followers_count = target.follower_links.filter(follower__profile__is_hidden=False).count()
        return Response({"following": created, "followers_count": followers_count})


class ConnectionsView(generics.ListAPIView):
    serializer_class = UserSummarySerializer

    def get_queryset(self):
        user = generics.get_object_or_404(User.objects.select_related("profile"), username=self.kwargs["username"], is_active=True)
        if user.profile.is_hidden and user != self.request.user:
            raise Http404

        kind = self.kwargs["kind"]
        if kind == "followers":
            ids = user.follower_links.values_list("follower_id", flat=True)
        elif kind == "following":
            ids = user.following_links.values_list("following_id", flat=True)
        else:
            raise Http404

        blocked, blocked_by = blocked_user_ids(self.request.user)
        return (
            User.objects.select_related("profile")
            .filter(pk__in=ids, is_active=True, profile__is_hidden=False)
            .exclude(pk__in=blocked)
            .exclude(pk__in=blocked_by)
            .order_by("profile__display_name", "username")
        )


class BlockView(APIView):
    def post(self, request, username):
        target = generics.get_object_or_404(User, username=username, is_active=True)
        if target == request.user:
            return Response({"detail": "Ação inválida."}, status=status.HTTP_400_BAD_REQUEST)
        block, created = Block.objects.get_or_create(blocker=request.user, blocked=target)
        if created:
            Follow.objects.filter(Q(follower=request.user, following=target) | Q(follower=target, following=request.user)).delete()
        else:
            block.delete()
        return Response({"blocked": created})
