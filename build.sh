#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

pip install -r requirements.txt
python manage.py collectstatic --noinput

# Refuse to run production migrations against an unexpected database target.
# This check intentionally runs before `migrate` so a bad DATABASE_URL cannot
# mutate a fallback or legacy database by accident.
python manage.py check_database_target
python manage.py migrate
python manage.py check_integrations

# Superuser creation is a recovery/bootstrap action, not a normal build step.
# It runs only when explicitly enabled for one deploy.
if [[ "${PULSO_BOOTSTRAP_SUPERUSER:-0}" == "1" ]]; then
  : "${DJANGO_SUPERUSER_USERNAME:?DJANGO_SUPERUSER_USERNAME is required}"
  : "${DJANGO_SUPERUSER_EMAIL:?DJANGO_SUPERUSER_EMAIL is required}"
  : "${DJANGO_SUPERUSER_PASSWORD:?DJANGO_SUPERUSER_PASSWORD is required}"
  python manage.py createsuperuser --noinput
fi
