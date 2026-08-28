from django.urls import path

from .views import app_shell, auth_page, landing, pwa_manifest, security_page, service_worker

urlpatterns = [
    path("manifest.webmanifest", pwa_manifest, name="pwa-manifest"),
    path("service-worker.js", service_worker, name="service-worker"),
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
