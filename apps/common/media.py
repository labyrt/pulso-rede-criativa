"""Safe image validation and storage for user-generated PULSO media."""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import uuid4

import requests
from django.conf import settings
from django.core.files.storage import default_storage
from PIL import Image, UnidentifiedImageError


MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


class MediaUploadError(ValueError):
    """Raised when an uploaded asset cannot be validated or persisted."""


def validate_image(uploaded_file):
    if uploaded_file.size > MAX_IMAGE_BYTES:
        raise MediaUploadError("A imagem deve ter no máximo 8 MB.")

    content_type = (getattr(uploaded_file, "content_type", "") or "").lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise MediaUploadError("Envie uma imagem JPG, PNG ou WebP.")

    try:
        uploaded_file.seek(0)
        with Image.open(uploaded_file) as image:
            image.verify()
        uploaded_file.seek(0)
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise MediaUploadError("O arquivo enviado não é uma imagem válida.") from exc
    return uploaded_file


def _cloudinary_config():
    value = os.getenv("CLOUDINARY_URL", "").strip()
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme != "cloudinary" or not parsed.username or not parsed.password or not parsed.hostname:
        raise MediaUploadError("A configuração do armazenamento de imagens é inválida.")
    return unquote(parsed.username), unquote(parsed.password), parsed.hostname


def _upload_to_cloudinary(uploaded_file, folder):
    api_key, api_secret, cloud_name = _cloudinary_config()
    timestamp = int(time.time())
    public_id = uuid4().hex
    signed = f"folder=pulso/{folder}&public_id={public_id}&timestamp={timestamp}{api_secret}"
    signature = hashlib.sha1(signed.encode("utf-8"), usedforsecurity=False).hexdigest()
    try:
        response = requests.post(
            f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload",
            data={
                "api_key": api_key,
                "timestamp": timestamp,
                "folder": f"pulso/{folder}",
                "public_id": public_id,
                "signature": signature,
            },
            files={"file": (Path(uploaded_file.name).name, uploaded_file, uploaded_file.content_type)},
            timeout=30,
        )
        response.raise_for_status()
        secure_url = response.json().get("secure_url", "")
        if not secure_url.startswith("https://"):
            raise MediaUploadError("O serviço de mídia não retornou uma URL segura.")
        return secure_url
    except (requests.RequestException, ValueError, KeyError) as exc:
        raise MediaUploadError("Não foi possível armazenar a imagem. Tente novamente.") from exc


def store_image(uploaded_file, folder, request=None):
    """Validate and persist an image, returning an HTTPS URL when possible."""

    validate_image(uploaded_file)
    if _cloudinary_config():
        return _upload_to_cloudinary(uploaded_file, folder)

    if not settings.DEBUG:
        raise MediaUploadError("O armazenamento de imagens ainda não foi conectado.")

    extension = ALLOWED_IMAGE_TYPES[uploaded_file.content_type.lower()]
    relative_path = f"uploads/{folder}/{uuid4().hex}{extension}"
    saved_path = default_storage.save(relative_path, uploaded_file)
    url = default_storage.url(saved_path)
    return request.build_absolute_uri(url) if request else url
