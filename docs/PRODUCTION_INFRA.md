# PULSO — production infrastructure

This document records the current production source of truth and the safeguards that prevent accidental infrastructure drift.

## Production topology

- Web application: Render web service `pulso-rede-criativa`, region Virginia.
- Runtime: Python / Django ASGI with Daphne.
- Primary database: Neon project `pulso-production`, branch `production`, database `pulso`.
- Cache / Channels: Render Key Value service `pulso-cache`.
- Static files: WhiteNoise during the application deploy.
- Health endpoint: `/health/` verifies the configured database target, live database connectivity and Redis readiness.

## Database source of truth

Neon is the only production database source of truth.

`DATABASE_URL` is a secret environment variable stored in Render and is intentionally declared with `sync: false` in `render.yaml`. The Blueprint does not create, reference or depend on Render Postgres.

Before migrations run, `python manage.py check_database_target` validates that:

1. `DATABASE_URL` is a valid PostgreSQL URL.
2. The host belongs to Neon when `PULSO_REQUIRE_NEON_DATABASE=1`.
3. The configured database name matches `PULSO_EXPECTED_DATABASE_NAME`.
4. A real connection can be established and PostgreSQL reports the expected database.

If any of these checks fail, the build stops before `migrate` can modify a database.

The runtime `/health/` endpoint uses the same target validation and returns a degraded status if database configuration drifts after deployment.

## Secrets that must remain stable

Never commit secret values to Git.

The following values must be preserved in the deployment environment and in a secure recovery record:

- `DATABASE_URL`
- `DJANGO_SECRET_KEY`
- `FIELD_ENCRYPTION_KEY`
- OAuth client secrets
- Cloudinary credentials
- third-party API credentials

`FIELD_ENCRYPTION_KEY` is especially important: changing it can make previously encrypted profile fields unreadable. For this reason, the Blueprint uses `sync: false` instead of generating a new value during service recreation.

## Build safety

The production build order is:

1. Install pinned dependencies.
2. Collect static files.
3. Validate the database target.
4. Apply Django migrations.
5. Print a non-secret integration readiness summary.
6. Optionally bootstrap a superuser only when `PULSO_BOOTSTRAP_SUPERUSER=1` is explicitly enabled.

The completed Render-to-Neon data-copy command is no longer part of the normal build path. It remains in the repository only as migration/recovery history. One-time migration flags such as `PULSO_COPY_DATABASE_TO_NEON` must stay disabled during normal production deploys.

## Rollback database

The legacy Render Postgres instance can be retained temporarily during the rollback window, but the application must not reference it. Removing the database declaration from `render.yaml` prevents a future Blueprint sync from recreating or reconnecting production to that database.

After the rollback window has closed and data integrity in Neon has been independently confirmed, the legacy Render database can be removed manually from the Render Dashboard.

## Deployment rule

Production deploys should be allowed only after CI and security checks pass. Infrastructure changes should be developed on a branch, tested, and merged into `main` only after validation.
