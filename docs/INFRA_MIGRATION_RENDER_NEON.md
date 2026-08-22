# PULSO — Render PostgreSQL to Neon migration

This migration is intentionally designed as a two-phase cutover.

## Safety model

- Render remains the source of truth until verification passes.
- `DATABASE_URL` is not modified by the migration command.
- The copy only runs when `PULSO_COPY_DATABASE_TO_NEON=1` is explicitly set.
- `NEON_DATABASE_URL` is supplied only as a secret environment variable.
- The target is migrated, flushed, loaded, and verified before cutover.
- Verification compares row counts for all migrated managed models.
- The temporary fixture exists only in an ephemeral build directory and is deleted automatically.

## Cutover sequence

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

`FIELD_ENCRYPTION_KEY` must remain unchanged during the migration because encrypted profile data depends on the same key for decryption.
