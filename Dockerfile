FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN addgroup --system pulso && adduser --system --ingroup pulso pulso
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput && chown -R pulso:pulso /app

USER pulso
EXPOSE 8000
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
