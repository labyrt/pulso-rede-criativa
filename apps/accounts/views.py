import logging

from allauth.account.models import EmailAddress
from allauth.account.utils import send_email_confirmation
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.social.models import Notification
from apps.webapp.throttles import AuthRateThrottle

from .media_serializers import ProfileMediaUpdateSerializer
from .models import Block, Follow, User
from .serializers import ProfileUpdateSerializer, PublicProfileSerializer, RegisterSerializer, UserSummarySerializer


logger = logging.getLogger(__name__)


def _email_verification_required():
    return settings.ACCOUNT_EMAIL_VERIFICATION == "mandatory"


def _email_verification_allows_login(user):
    """Require proof for new accounts without inventing proof for legacy users.

    Accounts created before verified-email rollout have no allauth EmailAddress
    record. They retain access. New local registrations create an EmailAddress
    when confirmation is sent; if that row exists and is not verified, login is
    blocked until the confirmation succeeds.
    """

    address = EmailAddress.objects.filter(user=user, email__iexact=user.email).first()
    return address is None or address.verified


def _has_verified_primary_email(user):
    return EmailAddress.objects.filter(user=user, email__iexact=user.email, verified=True).exists()


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        user = User.objects.get(username=response.data["username"])
        if _email_verification_required():
            send_email_confirmation(request._request, user, signup=True)
            return Response(
                {
                    "requires_email_verification": True,
                    "detail": "Conta criada. Confirme o link enviado ao seu e-mail antes de entrar.",
                },
                status=status.HTTP_201_CREATED,
            )
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
        if _email_verification_required() and not _email_verification_allows_login(user):
            return Response(
                {"detail": "Confirme seu e-mail antes de entrar.", "requires_email_verification": True},
                status=status.HTTP_403_FORBIDDEN,
            )
        login(request, user)
        return Response(PublicProfileSerializer(user.profile, context={"request": request}).data)


@method_decorator(csrf_protect, name="dispatch")
class ResendVerificationView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=True).first() if email else None
        if user and not _has_verified_primary_email(user):
            try:
                send_email_confirmation(request._request, user, signup=False)
            except Exception:
                # Never reveal whether a submitted address maps to an account.
                logger.exception("Email verification resend failed")
        return Response(
            {"detail": "Se houver uma conta pendente para esse e-mail, enviaremos uma nova confirmação."},
            status=status.HTTP_200_OK,
        )


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
        from .models import Profile

        return Profile.objects.select_related("user").filter(user__is_active=True)


class DiscoverCreatorsView(generics.ListAPIView):
    serializer_class = UserSummarySerializer
    search_fields = ["username", "profile__display_name", "profile__specialty", "profile__bio"]

    def get_queryset(self):
        blocked = Block.objects.filter(blocker=self.request.user).values_list("blocked_id", flat=True)
        return User.objects.select_related("profile").filter(is_active=True).exclude(pk=self.request.user.pk).exclude(pk__in=blocked).order_by("?")


class FollowView(APIView):
    def post(self, request, username):
        target = generics.get_object_or_404(User, username=username, is_active=True)
        if target == request.user:
            return Response({"detail": "Você não pode seguir a si mesma."}, status=status.HTTP_400_BAD_REQUEST)
        if Block.objects.filter(Q(blocker=request.user, blocked=target) | Q(blocker=target, blocked=request.user)).exists():
            return Response({"detail": "Esta conexão não está disponível."}, status=status.HTTP_403_FORBIDDEN)
        follow, created = Follow.objects.get_or_create(follower=request.user, following=target)
        if created:
            Notification.objects.create(recipient=target, actor=request.user, kind=Notification.Kind.FOLLOW)
        else:
            follow.delete()
        return Response({"following": created, "followers_count": target.follower_links.count()})


class ConnectionsView(generics.ListAPIView):
    serializer_class = UserSummarySerializer

    def get_queryset(self):
        user = generics.get_object_or_404(User, username=self.kwargs["username"], is_active=True)
        if self.kwargs["kind"] == "followers":
            ids = user.follower_links.values_list("follower_id", flat=True)
        else:
            ids = user.following_links.values_list("following_id", flat=True)
        return User.objects.select_related("profile").filter(pk__in=ids)


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
