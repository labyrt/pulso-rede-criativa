import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from django.apps import apps
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connection


APP_LABELS = [
    "accounts",
    "social",
    "chat",
    "payments",
    "assistant",
    "webapp",
    "sites",
    "account",
    "socialaccount",
    "authtoken",
]


class Command(BaseCommand):
    help = "Safely copy PULSO production data from the current database to Neon and verify row counts."

    def add_arguments(self, parser):
        parser.add_argument("--verify-manifest", default="")

    def handle(self, *args, **options):
        manifest_path = options.get("verify_manifest") or ""
        if manifest_path:
            self._verify_manifest(Path(manifest_path))
            return

        if os.getenv("PULSO_COPY_DATABASE_TO_NEON", "") != "1":
            raise CommandError("Migration guard is disabled. Set PULSO_COPY_DATABASE_TO_NEON=1 for the one-time copy.")

        target_url = os.getenv("NEON_DATABASE_URL", "").strip()
        if not target_url:
            raise CommandError("NEON_DATABASE_URL is required.")

        source_url = os.getenv("DATABASE_URL", "").strip()
        if not source_url:
            raise CommandError("DATABASE_URL is required for the Render source database.")

        source_host = urlparse(source_url).hostname
        target_host = urlparse(target_url).hostname
        if not source_host or not target_host:
            raise CommandError("Could not validate source and target database hosts.")
        if source_host == target_host:
            raise CommandError("Source and target database hosts are identical; refusing to continue.")

        if connection.vendor != "postgresql":
            raise CommandError("The source database is not PostgreSQL; refusing production migration.")

        self.stdout.write(f"Source database host validated: {source_host}")
        self.stdout.write(f"Target database host validated: {target_host}")

        with tempfile.TemporaryDirectory(prefix="pulso-neon-migration-") as tmpdir:
            tmp = Path(tmpdir)
            fixture_path = tmp / "pulso-data.json"
            manifest_path = tmp / "manifest.json"

            source_manifest = self._build_manifest()
            manifest_path.write_text(json.dumps(source_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            self.stdout.write("Creating an ephemeral fixture from the Render database...")
            call_command(
                "dumpdata",
                *APP_LABELS,
                database="default",
                natural_foreign=True,
                natural_primary=True,
                indent=2,
                output=str(fixture_path),
                verbosity=1,
            )

            target_env = os.environ.copy()
            target_env["DATABASE_URL"] = target_url
            target_env["PULSO_COPY_DATABASE_TO_NEON"] = "0"

            self._run_target(["migrate", "--noinput"], target_env)
            self._run_target(["flush", "--noinput"], target_env)
            # django.contrib.sites recreates a default Site after flush. The source
            # Site fixture must replace it so social-login relations preserve the
            # exact production Site configuration.
            self._run_target(
                [
                    "shell",
                    "-c",
                    "from django.contrib.sites.models import Site; Site.objects.all().delete()",
                ],
                target_env,
            )
            self._run_target(["loaddata", str(fixture_path)], target_env)
            self._run_target(["migrate_render_to_neon", "--verify-manifest", str(manifest_path)], target_env)
            self._run_target(["check", "--deploy"], target_env, allow_nonzero=True)

        self.stdout.write(self.style.SUCCESS("PULSO_NEON_COPY_VERIFIED"))

    def _run_target(self, manage_args, env, allow_nonzero=False):
        command = [sys.executable, "manage.py", *manage_args]
        self.stdout.write("Target: " + " ".join(manage_args))
        result = subprocess.run(command, env=env, text=True, capture_output=True)
        if result.stdout:
            self.stdout.write(result.stdout.rstrip())
        if result.stderr:
            self.stderr.write(result.stderr.rstrip())
        if result.returncode != 0 and not allow_nonzero:
            raise CommandError(f"Target command failed: {' '.join(manage_args)}")
        return result

    def _models(self):
        for app_label in APP_LABELS:
            try:
                app_config = apps.get_app_config(app_label)
            except LookupError:
                continue
            for model in app_config.get_models():
                if model._meta.managed and not model._meta.proxy:
                    yield model

    def _build_manifest(self):
        manifest = {}
        for model in self._models():
            key = model._meta.label_lower
            count = model._default_manager.using("default").count()
            manifest[key] = count
            self.stdout.write(f"Source count {key}: {count}")
        return manifest

    def _verify_manifest(self, manifest_path):
        if not manifest_path.exists():
            raise CommandError("Verification manifest does not exist.")
        expected = json.loads(manifest_path.read_text(encoding="utf-8"))
        mismatches = []
        for model in self._models():
            key = model._meta.label_lower
            if key not in expected:
                continue
            actual = model._default_manager.using("default").count()
            wanted = int(expected[key])
            self.stdout.write(f"Target count {key}: {actual} (expected {wanted})")
            if actual != wanted:
                mismatches.append((key, wanted, actual))

        if mismatches:
            details = ", ".join(f"{key}: expected {wanted}, got {actual}" for key, wanted, actual in mismatches)
            raise CommandError("Database copy verification failed: " + details)

        self.stdout.write(self.style.SUCCESS("Target row-count verification passed for all migrated models."))
