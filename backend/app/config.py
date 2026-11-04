import os
from pathlib import Path
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


class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", DEV_SECRET_FALLBACK)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
    JSON_SORT_KEYS = False
    RATELIMIT_ENABLED = True
    RATELIMIT_LOGIN_LIMIT = int(os.environ.get("RATELIMIT_LOGIN_LIMIT", 5))
    RATELIMIT_LOGIN_PERIOD = int(os.environ.get("RATELIMIT_LOGIN_PERIOD", 60))
    RATELIMIT_ORDER_LIMIT = int(os.environ.get("RATELIMIT_ORDER_LIMIT", 10))
    RATELIMIT_ORDER_PERIOD = int(os.environ.get("RATELIMIT_ORDER_PERIOD", 60))
    # Number of trusted upstream reverse proxies (e.g., 1 if behind Nginx or AWS ALB; 0 for direct connection)
    TRUSTED_PROXIES_COUNT = int(os.environ.get("TRUSTED_PROXIES_COUNT", 0))


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    database_dir = BASE_DIR / "instance"
    database_dir.mkdir(parents=True, exist_ok=True)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{database_dir / 'store.db'}"
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
    database_dir = BASE_DIR / "instance"
    database_dir.mkdir(parents=True, exist_ok=True)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{database_dir / 'store.db'}"
    )
    # Production strictly requires explicit secrets and CORS origins
    SECRET_KEY = os.environ.get("SECRET_KEY")
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
