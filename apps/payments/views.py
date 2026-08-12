from io import BytesIO

import qrcode
import qrcode.image.svg
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User

from .models import SupportIntent
from .pix import build_pix_payload
from .serializers import SupportIntentSerializer


class PixView(APIView):
    def get(self, request, username):
        creator = get_object_or_404(User.objects.select_related("profile"), username=username, is_active=True)
        profile = creator.profile
        if not (profile.pix_key and profile.pix_receiver_name and profile.pix_city):
            return Response({"detail": "Este perfil ainda não ativou o apoio por Pix."}, status=status.HTTP_404_NOT_FOUND)
        amount = request.query_params.get("amount")
        try:
            amount_value = float(amount) if amount else None
        except ValueError:
            return Response({"detail": "Valor inválido."}, status=status.HTTP_400_BAD_REQUEST)
        payload = build_pix_payload(profile.pix_key, profile.pix_receiver_name, profile.pix_city, amount_value)
        qr = qrcode.make(payload, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=2)
        buffer = BytesIO()
        qr.save(buffer)
        svg = buffer.getvalue().decode("utf-8")
        return Response({"payload": payload, "qr_svg": svg, "creator": profile.name})


class SupportIntentView(APIView):
    def post(self, request, username):
        creator = get_object_or_404(User, username=username, is_active=True)
        serializer = SupportIntentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        intent = serializer.save(supporter=request.user, creator=creator)
        return Response(SupportIntentSerializer(intent).data, status=status.HTTP_201_CREATED)
