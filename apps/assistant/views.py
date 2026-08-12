import random

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.webapp.throttles import AIRateThrottle


LOCAL_OPENINGS = [
    "Por trás deste trabalho existe uma escolha que mudou tudo:",
    "Um recorte do processo antes de ele virar resultado:",
    "Criei isto para quem também acredita que estilo é linguagem.",
    "Nem todo detalhe pede atenção. Este pediu.",
]


class CaptionAssistantView(APIView):
    throttle_classes = [AIRateThrottle]

    def post(self, request):
        draft = str(request.data.get("draft", "")).strip()[:800]
        category = str(request.data.get("category", "arte"))[:40]
        tone = str(request.data.get("tone", "autêntico"))[:30]
        if not draft:
            return Response({"detail": "Escreva uma ideia inicial para receber ajuda."}, status=status.HTTP_400_BAD_REQUEST)

        if settings.GEMINI_API_KEY:
            try:
                from google import genai

                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                prompt = (
                    "Você é uma editora brasileira de conteúdo para artistas independentes. "
                    "Reescreva o rascunho em português do Brasil, com voz humana, específica e sem clichês. "
                    "Máximo 450 caracteres; sem emojis em excesso; inclua até 3 hashtags úteis. "
                    "Nunca invente fatos, clientes ou resultados. Retorne somente a legenda.\n\n"
                    f"Categoria: {category}\nTom: {tone}\nRascunho: {draft}"
                )
                result = client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt)
                suggestion = (result.text or "").strip()[:500]
                if suggestion:
                    return Response({"suggestion": suggestion, "provider": "gemini"})
            except Exception:
                pass

        tags = [word.lower().strip(".,!?:;#") for word in draft.split() if len(word) > 6][:2]
        hashtags = " ".join(f"#{tag}" for tag in dict.fromkeys([category.replace(" ", ""), *tags]) if tag)
        suggestion = f"{random.choice(LOCAL_OPENINGS)} {draft.rstrip('.')} — {hashtags}".strip()
        return Response({"suggestion": suggestion[:500], "provider": "local"})
