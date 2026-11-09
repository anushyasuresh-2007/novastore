import os
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

# Base directory for backend
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")

DEV_SECRET_FALLBACK = "dev-secret-key-change-in-production"
INSECURE_SECRET_KEYS = {
    DEV_SECRET_FALLBACK,
    "change-this-to-a-secure-random-key-in-production",
}
MIN_PRODUCTION_SECRET_KEY_LENGTH = 32

SUPPORTED_PRODUCTION_DATABASE_SCHEMES = ("postgresql", "postgres", "postgresql+psycopg2")


def normalize_database_url(url: str | None) -> str | None:
    """Normalize database connection URL to ensure dialect compatibility (e.g. postgres:// or postgresql:// -> postgresql+psycopg2://)."""
    if not url or not str(url).strip():
        return None
    clean_url = str(url).strip()
    if clean_url.startswith("postgres://"):
        return clean_url.replace("postgres://", "postgresql+psycopg2://", 1)
    if clean_url.startswith("postgresql://"):
        return clean_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return clean_url


def validate_production_database_url(url: str | None) -> str:
    """Validate and normalize DATABASE_URL for production deployment.

    Raises RuntimeError if URL is missing, empty, malformed, or uses an unsupported scheme.
    Credentials and query parameters are never echoed into error messages.
    """
    if not url or not str(url).strip():
        raise RuntimeError(
            "CRITICAL CONFIGURATION ERROR: DATABASE_URL is not configured for production. "
            "Application startup aborted. An explicit PostgreSQL database URL must be provided."
        )

    clean_url = str(url).strip()
    try:
        parsed = urlparse(clean_url)
    except Exception as exc:
        raise RuntimeError(
            f"CRITICAL CONFIGURATION ERROR: Malformed DATABASE_URL: {exc}"
        ) from exc

    if not parsed.scheme:
        raise RuntimeError(
            "CRITICAL CONFIGURATION ERROR: Malformed DATABASE_URL: missing URL scheme. "
            "Production requires a PostgreSQL database (postgresql:// or postgres://)."
        )

    scheme_lower = parsed.scheme.lower()
    if scheme_lower not in SUPPORTED_PRODUCTION_DATABASE_SCHEMES:
        raise RuntimeError(
            f"CRITICAL CONFIGURATION ERROR: Unsupported database scheme '{parsed.scheme}'. "
            "Production requires a PostgreSQL database (postgresql:// or postgres://)."
        )

    if not parsed.netloc:
        raise RuntimeError(
            "CRITICAL CONFIGURATION ERROR: Malformed DATABASE_URL: missing database host/network location."
        )

    # Normalize postgres:// or postgresql:// to postgresql+psycopg2:// for psycopg2 driver compatibility
    if clean_url.startswith("postgres://"):
        clean_url = clean_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif clean_url.startswith("postgresql://"):
        clean_url = clean_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    return clean_url


class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", DEV_SECRET_FALLBACK)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
    JSON_SORT_KEYS = False
    RATELIMIT_ENABLED = True
    RATELIMIT_ADMIN_LOGIN_LIMIT = int(
        os.environ.get("RATELIMIT_ADMIN_LOGIN_LIMIT")
        or os.environ.get("RATELIMIT_LOGIN_LIMIT", 5)
    )
    RATELIMIT_ADMIN_LOGIN_PERIOD = int(
        os.environ.get("RATELIMIT_ADMIN_LOGIN_PERIOD")
        or os.environ.get("RATELIMIT_LOGIN_PERIOD", 60)
    )
    RATELIMIT_ORDER_CREATE_LIMIT = int(
        os.environ.get("RATELIMIT_ORDER_CREATE_LIMIT")
        or os.environ.get("RATELIMIT_ORDER_LIMIT", 10)
    )
    RATELIMIT_ORDER_CREATE_PERIOD = int(
        os.environ.get("RATELIMIT_ORDER_CREATE_PERIOD")
        or os.environ.get("RATELIMIT_ORDER_PERIOD", 60)
    )
    # Maintain legacy aliases for backwards compatibility
    RATELIMIT_LOGIN_LIMIT = RATELIMIT_ADMIN_LOGIN_LIMIT
    RATELIMIT_LOGIN_PERIOD = RATELIMIT_ADMIN_LOGIN_PERIOD
    RATELIMIT_ORDER_LIMIT = RATELIMIT_ORDER_CREATE_LIMIT
    RATELIMIT_ORDER_PERIOD = RATELIMIT_ORDER_CREATE_PERIOD
    # Number of trusted upstream reverse proxies (e.g., 0 for direct connection or unknown upstream).
    # NOTE: Hosting provider proxy chains (e.g., Render, Cloudflare, AWS ALB) must be verified
    # against official provider documentation before configuring in production.
    # Default is 0: untrusted forwarded headers (X-Forwarded-For, etc.) will be strictly ignored.
    TRUSTED_PROXIES_COUNT = int(os.environ.get("TRUSTED_PROXIES_COUNT", 0))


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    database_dir = BASE_DIR / "instance"
    database_dir.mkdir(parents=True, exist_ok=True)
    _default_db = f"sqlite:///{database_dir / 'store.db'}"
    SQLALCHEMY_DATABASE_URI = (
        normalize_database_url(os.environ.get("DATABASE_URL"))
        or _default_db
    )
    CORS_ORIGINS = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    )


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    DEBUG = True
    SECRET_KEY = os.environ.get("SECRET_KEY", "test-secret-key-for-testing-only")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL",
        "sqlite:///:memory:"
    )
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
    RATELIMIT_ENABLED = False
    TRUSTED_PROXIES_COUNT = 0


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    ENV = "production"
    # Production strictly requires an explicitly supplied DATABASE_URL; no silent fallback to SQLite
    SQLALCHEMY_DATABASE_URI = normalize_database_url(os.environ.get("DATABASE_URL"))
    # Production strictly requires explicit secrets and CORS origins
    SECRET_KEY = os.environ.get("SECRET_KEY")
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
