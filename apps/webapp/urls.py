from django.urls import path

from .native_auth_views import native_auth_complete, native_auth_consume, native_auth_start
from .views import app_shell, auth_page, landing, pwa_manifest, security_page, service_worker
from .widget_views import WidgetSummaryView

urlpatterns = [
    path("manifest.webmanifest", pwa_manifest, name="pwa-manifest"),
    path("service-worker.js", service_worker, name="service-worker"),
    path("api/v1/widget/summary/", WidgetSummaryView.as_view(), name="widget-summary"),
    path("native-auth/start/<str:provider>/", native_auth_start, name="native-auth-start"),
    path("native-auth/complete/", native_auth_complete, name="native-auth-complete"),
    path("native-auth/consume/", native_auth_consume, name="native-auth-consume"),
    path("", landing, name="landing"),
    path("entrar/", auth_page, {"mode": "login"}, name="login-page"),
    path("criar-conta/", auth_page, {"mode": "register"}, name="register-page"),
    path("app/", app_shell, {"section": "feed"}, name="app"),
    path("explorar/", app_shell, {"section": "explore"}, name="explore-page"),
    path("favoritos/", app_shell, {"section": "bookmarks"}, name="bookmarks-page"),
    path("notificacoes/", app_shell, {"section": "notifications"}, name="notifications-page"),
    path("mensagens/", app_shell, {"section": "messages"}, name="messages-page"),
    path("perfil/<str:username>/", app_shell, {"section": "profile"}, name="profile-page"),
    path("seguranca/", security_page, name="security-page"),
]
