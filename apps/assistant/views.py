import logging
import re

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.webapp.throttles import AIRateThrottle


logger = logging.getLogger("pulso.assistant")

_GENERIC_OPENINGS = (
    "por trás deste trabalho existe uma escolha que mudou tudo",
    "um recorte do processo antes de ele virar resultado",
    "criei isto para quem também acredita que estilo é linguagem",
    "nem todo detalhe pede atenção. este pediu",
)


def local_editor_fallback(draft):
    """Degrade safely without pretending a template is AI-generated copy."""
    text = str(draft or "").strip()
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:800].rstrip()


def build_caption_prompt(*, draft, category, tone, mode):
    return (
        "Você é uma editora brasileira de conteúdo para uma rede de criadores independentes. "
        "Sua função é lapidar a voz de quem escreveu, não substituir essa voz por copy genérica. "
        "Preserve fatos, intenção, ritmo, vocabulário e estranhezas interessantes do rascunho. "
        "Não invente contexto, clientes, resultados, materiais, sentimentos ou objetivos. "
        "Não force gancho, CTA, frase de efeito, tom publicitário ou estrutura de LinkedIn/Instagram. "
        "Evite clichês como 'por trás deste trabalho', 'um recorte do processo', 'estilo é linguagem' "
        "e 'nem todo detalhe pede atenção'. Se o texto já estiver bom, faça mudanças mínimas. "
        "Use hashtags somente quando acrescentarem descoberta real; nunca extraia hashtags só porque uma palavra é longa. "
        "Máximo de 3 hashtags e elas são opcionais. Sem emojis salvo se já fizerem parte da voz do rascunho. "
        "Escreva em português do Brasil e retorne somente a legenda final, sem aspas nem explicações. "
        "Mantenha preferencialmente até 450 caracteres, mas priorize coerência sobre fórmulas.\n\n"
        f"Modo editorial: {mode}\n"
        f"Categoria: {category}\n"
        f"Tom pedido: {tone}\n"
        "--- RASCUNHO DO USUÁRIO ---\n"
        f"{draft}\n"
        "--- FIM DO RASCUNHO ---"
    )


def looks_canned(text):
    normalized = re.sub(r"\s+", " ", str(text or "").strip().lower())
    return any(opening in normalized for opening in _GENERIC_OPENINGS)


class CaptionAssistantView(APIView):
    throttle_classes = [AIRateThrottle]

    def post(self, request):
        draft = str(request.data.get("draft", "")).strip()[:800]
        category = str(request.data.get("category", "arte")).strip()[:40] or "arte"
        tone = str(request.data.get("tone", "autêntico")).strip()[:60] or "autêntico"
        mode = str(request.data.get("mode", "natural")).strip().lower()[:20] or "natural"
        if mode not in {"natural", "editorial", "direto"}:
            mode = "natural"
        if not draft:
            return Response(
                {"detail": "Escreva uma ideia inicial para receber ajuda."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if settings.GEMINI_API_KEY:
            try:
                from google import genai

                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                result = client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=build_caption_prompt(
                        draft=draft,
                        category=category,
                        tone=tone,
                        mode=mode,
                    ),
                )
                suggestion = (result.text or "").strip()[:800]
                if suggestion and not looks_canned(suggestion):
                    return Response(
                        {
                            "suggestion": suggestion,
                            "provider": "gemini",
                            "degraded": False,
                        }
                    )
                logger.warning(
                    "Caption provider returned empty or canned output model=%s",
                    settings.GEMINI_MODEL,
                )
            except Exception:
                logger.exception(
                    "Caption provider failed model=%s",
                    settings.GEMINI_MODEL,
                )
        else:
            logger.warning("Caption provider unavailable because GEMINI_API_KEY is not configured")

        return Response(
            {
                "suggestion": local_editor_fallback(draft),
                "provider": "local",
                "degraded": True,
            }
        )
