# PULSO — Render PostgreSQL to Neon migration

## Status

The production cutover to Neon has been completed and verified. Neon is now the production source of truth. The procedure below is retained as migration history and a recovery reference; it is **not** part of the normal deployment path anymore.

The production build now validates the Neon target before running Django migrations. See `docs/PRODUCTION_INFRA.md` for the current topology and safeguards.

## Original migration safety model

This migration was intentionally designed as a two-phase cutover.

- Render remained the source of truth until verification passed.
- `DATABASE_URL` was not modified by the migration command.
- The copy ran only when `PULSO_COPY_DATABASE_TO_NEON=1` was explicitly set.
- `NEON_DATABASE_URL` was supplied only as a secret environment variable.
- The target was migrated, flushed, loaded, and verified before cutover.
- Verification compared row counts for all migrated managed models.
- The temporary fixture existed only in an ephemeral build directory and was deleted automatically.

## Original cutover sequence

1. Deploy the guarded migration code with the copy flag disabled.
2. Set `NEON_DATABASE_URL` to the Neon staging branch and enable the one-time copy flag.
3. Deploy once and require `PULSO_NEON_COPY_VERIFIED` in the logs.
4. Inspect the Neon staging database and application checks.
5. Disable the one-time copy flag.
6. Copy the verified database to the Neon production branch or repeat the guarded copy to the production branch.
7. Change `DATABASE_URL` only after verification.
8. Deploy and run production smoke tests.
9. Keep the Render database intact during the rollback window.

## Important secrets

Never commit `DATABASE_URL`, `NEON_DATABASE_URL`, `DJANGO_SECRET_KEY`, `FIELD_ENCRYPTION_KEY`, OAuth secrets, or provider credentials to the repository.

`FIELD_ENCRYPTION_KEY` must remain unchanged because encrypted profile data depends on the same key for decryption.
