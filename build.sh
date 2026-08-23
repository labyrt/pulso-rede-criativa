#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py check_integrations

# One-time, guarded Render -> Neon production data copy. This runs only when
# explicitly enabled in the Render environment and leaves DATABASE_URL untouched.
if [[ "${PULSO_COPY_DATABASE_TO_NEON:-0}" == "1" ]]; then
  python manage.py migrate_render_to_neon
fi

# Render Free não oferece Shell. Se estas variáveis secretas estiverem
# configuradas, cria o primeiro administrador sem publicar a senha.
if [[ -n "${DJANGO_SUPERUSER_USERNAME:-}" && -n "${DJANGO_SUPERUSER_EMAIL:-}" && -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]]; then
  python manage.py createsuperuser --noinput || true
fi
