from django.urls import path

from .views import PixView, SupportIntentView

urlpatterns = [
    path("<str:username>/pix/", PixView.as_view(), name="pix"),
    path("<str:username>/intent/", SupportIntentView.as_view(), name="support-intent"),
]
