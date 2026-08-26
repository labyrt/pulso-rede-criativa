from urllib.parse import urlparse


def validate_database_target(database_url, *, require_neon=False, expected_database=""):
    """Validate a database URL without exposing credentials in errors or logs."""
    database_url = (database_url or "").strip()
    expected_database = (expected_database or "").strip()

    if not database_url:
        raise ValueError("DATABASE_URL is not configured")

    parsed = urlparse(database_url)
    host = (parsed.hostname or "").lower().rstrip(".")
    database_name = parsed.path.lstrip("/")

    if parsed.scheme not in {"postgres", "postgresql"} or not host or not database_name:
        raise ValueError("DATABASE_URL is not a valid PostgreSQL connection URL")

    is_neon = host.endswith(".neon.tech")
    if require_neon and not is_neon:
        raise ValueError("DATABASE_URL does not point to Neon")

    if expected_database and database_name != expected_database:
        raise ValueError("DATABASE_URL points to an unexpected database name")

    return {
        "provider": "neon" if is_neon else "other",
        "database": database_name,
    }
