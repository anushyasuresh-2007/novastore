import os
import importlib
import pytest
import app.config
from app import create_app
from app.models.db import db
from app.models.admin import Admin
from app.services.rate_limiter import limiter
from app.services.auth_service import AuthService, DEFAULT_MAX_AGE_SECONDS
from create_admin import create_or_update_admin
from rotate_admin_password import rotate_admin_password


@pytest.fixture
def admin_user(app):
    """Fixture creating an active test admin."""
    with app.app_context():
        admin = Admin(username="sec_test_admin", email="sectest@example.com")
        admin.set_password("AdminSecurePass123!")
        db.session.add(admin)
        db.session.commit()
        return admin.id


# ============================================================================
# TASK 1: Production SECRET_KEY Enforcement Tests
# ============================================================================

def test_production_missing_secret_key_fails_startup(monkeypatch):
    """Test application startup strictly fails in production if SECRET_KEY is missing or empty."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("CORS_ORIGINS", "https://novastore-example.com")

    with pytest.raises(RuntimeError) as exc_info:
        create_app("production")

    err_msg = str(exc_info.value)
    assert "CRITICAL SECURITY ERROR" in err_msg
    assert "SECRET_KEY" in err_msg
    # Ensure no secret content is ever printed
    assert "dev-secret-key" not in err_msg


def test_production_empty_secret_key_fails_startup(monkeypatch):
    """Test startup fails when SECRET_KEY is an empty or whitespace string."""
    monkeypatch.setenv("SECRET_KEY", "   ")
    monkeypatch.setenv("CORS_ORIGINS", "https://novastore-example.com")

    with pytest.raises(RuntimeError) as exc_info:
        create_app("production")

    assert "CRITICAL SECURITY ERROR" in str(exc_info.value)
    assert "SECRET_KEY is not configured" in str(exc_info.value)


@pytest.mark.parametrize("insecure_fallback", [
    "dev-secret-key-change-in-production",
    "change-this-to-a-secure-random-key-in-production",
])
def test_production_default_fallback_secret_key_rejected(monkeypatch, insecure_fallback):
    """Test startup strictly rejects known development fallback secret keys in production."""
    monkeypatch.setenv("SECRET_KEY", insecure_fallback)
    monkeypatch.setenv("CORS_ORIGINS", "https://novastore-example.com")

    with pytest.raises(RuntimeError) as exc_info:
        create_app("production")

    err_msg = str(exc_info.value)
    assert "CRITICAL SECURITY ERROR" in err_msg
    assert "Insecure or default development SECRET_KEY cannot be used in production" in err_msg
    # Crucial safety check: ensure the secret string itself is not printed
    assert insecure_fallback not in err_msg


def test_production_secret_key_too_short_rejected(monkeypatch):
    """Test production startup strictly rejects SECRET_KEY shorter than 32 characters."""
    short_key = "short-secret-under-32-chars!"  # 28 characters
    monkeypatch.setenv("SECRET_KEY", short_key)
    monkeypatch.setenv("CORS_ORIGINS", "https://novastore-example.com")

    with pytest.raises(RuntimeError) as exc_info:
        create_app("production")

    err_msg = str(exc_info.value)
    assert "CRITICAL SECURITY ERROR" in err_msg
    assert "must be at least 32 characters" in err_msg
    # Never print the actual secret key
    assert short_key not in err_msg


def test_production_valid_secret_key_accepted(monkeypatch):
    """Test application startup succeeds in production with a unique valid SECRET_KEY >= 32 chars."""
    safe_key = "a9f8b2c4e6d871350a4bf39801ec6d4352ab908e7f1234567890abcdef123456"
    monkeypatch.setenv("SECRET_KEY", safe_key)
    monkeypatch.setenv("CORS_ORIGINS", "https://novastore-example.com")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@ep-neon.tech/novastore_prod?sslmode=require")

    prod_app = create_app("production")
    assert prod_app is not None
    assert prod_app.config["SECRET_KEY"] == safe_key
    assert prod_app.config["DEBUG"] is False


def test_development_safe_fallback_retained(monkeypatch):
    """Test development configuration safely allows fallback key for frictionless local dev."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    dev_app = create_app("development")
    assert dev_app is not None
    assert dev_app.config["SECRET_KEY"] == "dev-secret-key-change-in-production"
    assert dev_app.config["DEBUG"] is True


def test_production_debug_mode_disabled(monkeypatch):
    """Test production application explicitly disables debug mode."""
    safe_key = "a9f8b2c4e6d871350a4bf39801ec6d4352ab908e7f1234567890abcdef123456"
    monkeypatch.setenv("SECRET_KEY", safe_key)
    monkeypatch.setenv("CORS_ORIGINS", "https://novastore-example.com")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@ep-neon.tech/novastore_prod?sslmode=require")
    prod_app = create_app("production")
    assert prod_app.config["DEBUG"] is False


# ============================================================================
# TASK 2: CORS Hardening Tests
# ============================================================================

@pytest.mark.parametrize("wildcard_cors", [
    "*",
    "https://example.com, *",
    "*, https://example.com",
])
def test_production_wildcard_cors_rejected(monkeypatch, wildcard_cors):
    """Test production mode strictly rejects wildcard origins ('*') in CORS configuration."""
    monkeypatch.setenv("SECRET_KEY", "valid-cryptographic-prod-secret-987654321")
    monkeypatch.setenv("CORS_ORIGINS", wildcard_cors)

    with pytest.raises(RuntimeError) as exc_info:
        create_app("production")

    assert "Wildcard CORS origin ('*') is strictly forbidden in production mode" in str(exc_info.value)


def test_production_missing_cors_origins_rejected(monkeypatch):
    """Test production mode strictly requires explicit CORS_ORIGINS."""
    monkeypatch.setenv("SECRET_KEY", "valid-cryptographic-prod-secret-987654321")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        create_app("production")

    assert "CORS_ORIGINS is not configured for production" in str(exc_info.value)


def test_production_explicit_cors_origins_accepted(monkeypatch):
    """Test production mode accepts explicit trusted origins and handles preflight."""
    monkeypatch.setenv("SECRET_KEY", "valid-cryptographic-prod-secret-987654321")
    monkeypatch.setenv("CORS_ORIGINS", "https://store.example.com, https://admin.example.com")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@ep-neon.tech/novastore_prod?sslmode=require")

    prod_app = create_app("production")
    client = prod_app.test_client()

    # Request from allowed origin
    res = client.get("/api/health", headers={"Origin": "https://store.example.com"})
    assert res.status_code == 200
    assert res.headers.get("Access-Control-Allow-Origin") == "https://store.example.com"
    assert res.headers.get("Access-Control-Allow-Credentials") == "true"


# ============================================================================
# TASK 2B: Production Database Fail-Safe Tests
# ============================================================================

def test_production_missing_database_url_fails_startup(monkeypatch):
    """Test production startup strictly fails when DATABASE_URL is missing."""
    monkeypatch.setenv("SECRET_KEY", "valid-cryptographic-prod-secret-987654321")
    monkeypatch.setenv("CORS_ORIGINS", "https://store.example.com")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        create_app("production")

    err_msg = str(exc_info.value)
    assert "CRITICAL CONFIGURATION ERROR" in err_msg
    assert "DATABASE_URL is not configured for production" in err_msg


@pytest.mark.parametrize("empty_val", ["", "   ", "\t\n"])
def test_production_empty_database_url_fails_startup(monkeypatch, empty_val):
    """Test production startup strictly fails when DATABASE_URL is empty or whitespace."""
    monkeypatch.setenv("SECRET_KEY", "valid-cryptographic-prod-secret-987654321")
    monkeypatch.setenv("CORS_ORIGINS", "https://store.example.com")
    monkeypatch.setenv("DATABASE_URL", empty_val)

    with pytest.raises(RuntimeError) as exc_info:
        create_app("production")

    err_msg = str(exc_info.value)
    assert "CRITICAL CONFIGURATION ERROR" in err_msg
    assert "DATABASE_URL is not configured for production" in err_msg


@pytest.mark.parametrize("unsupported_url", [
    "mysql://user:pass@localhost:3306/novastore",
    "sqlite:///store.db",
    "sqlite:///:memory:",
    "ftp://example.com/db.sqlite",
    "redis://localhost:6379/0",
    "not-a-valid-url-without-scheme",
])
def test_production_unsupported_database_url_scheme_fails_startup(monkeypatch, unsupported_url):
    """Test production startup strictly rejects unsupported database schemes and malformed URLs."""
    monkeypatch.setenv("SECRET_KEY", "valid-cryptographic-prod-secret-987654321")
    monkeypatch.setenv("CORS_ORIGINS", "https://store.example.com")
    monkeypatch.setenv("DATABASE_URL", unsupported_url)

    with pytest.raises(RuntimeError) as exc_info:
        create_app("production")

    err_msg = str(exc_info.value)
    assert "CRITICAL CONFIGURATION ERROR" in err_msg
    assert ("Unsupported database scheme" in err_msg or "missing URL scheme" in err_msg)


def test_production_malformed_database_url_missing_host_fails_startup(monkeypatch):
    """Test production startup rejects PostgreSQL URL missing host."""
    monkeypatch.setenv("SECRET_KEY", "valid-cryptographic-prod-secret-987654321")
    monkeypatch.setenv("CORS_ORIGINS", "https://store.example.com")
    monkeypatch.setenv("DATABASE_URL", "postgresql://")

    with pytest.raises(RuntimeError) as exc_info:
        create_app("production")

    err_msg = str(exc_info.value)
    assert "CRITICAL CONFIGURATION ERROR" in err_msg
    assert "missing database host" in err_msg


def test_production_postgres_url_normalization(monkeypatch):
    """Test postgres:// scheme is automatically normalized to postgresql+psycopg2:// in production."""
    monkeypatch.setenv("SECRET_KEY", "valid-cryptographic-prod-secret-987654321")
    monkeypatch.setenv("CORS_ORIGINS", "https://store.example.com")
    monkeypatch.setenv("DATABASE_URL", "postgres://neon_user:neon_pass@ep-cool.neon.tech:5432/novastore")

    prod_app = create_app("production")
    assert prod_app.config["SQLALCHEMY_DATABASE_URI"] == (
        "postgresql+psycopg2://neon_user:neon_pass@ep-cool.neon.tech:5432/novastore"
    )


def test_production_postgresql_url_preserved(monkeypatch):
    """Test valid postgresql:// URL with query parameters is normalized with psycopg2 driver."""
    valid_url = "postgresql://neon_user:neon_pass@ep-cool.neon.tech:5432/novastore?sslmode=require"
    monkeypatch.setenv("SECRET_KEY", "valid-cryptographic-prod-secret-987654321")
    monkeypatch.setenv("CORS_ORIGINS", "https://store.example.com")
    monkeypatch.setenv("DATABASE_URL", valid_url)

    prod_app = create_app("production")
    assert prod_app.config["SQLALCHEMY_DATABASE_URI"] == (
        "postgresql+psycopg2://neon_user:neon_pass@ep-cool.neon.tech:5432/novastore?sslmode=require"
    )


def test_development_retains_sqlite_default(monkeypatch):
    """Test development configuration defaults to local SQLite when DATABASE_URL is unset."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    dev_app = create_app("development")
    assert dev_app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///")
    assert "store.db" in dev_app.config["SQLALCHEMY_DATABASE_URI"]


def test_testing_retains_sqlite_in_memory_default(monkeypatch):
    """Test testing configuration defaults to in-memory SQLite when TEST_DATABASE_URL is unset."""
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    test_app = create_app("testing")
    assert test_app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


# ============================================================================
# TASK 3: Admin Password Policy (Minimum 8 Characters) Tests
# ============================================================================

def test_admin_model_password_length_enforcement(app):
    """Test Admin model rejects passwords shorter than 8 characters and accepts >= 8."""
    with app.app_context():
        admin = Admin(username="minpass_test", email="minpass@example.com")

        # 7 characters: rejected
        with pytest.raises(ValueError) as exc1:
            admin.set_password("Short7!")
        assert "at least 8 characters" in str(exc1.value)

        # 0 characters: rejected
        with pytest.raises(ValueError) as exc2:
            admin.set_password("")
        assert "at least 8 characters" in str(exc2.value)

        # 8 characters: accepted
        admin.set_password("Exact8!a")
        assert admin.password_hash is not None
        assert admin.check_password("Exact8!a") is True
        assert admin.check_password("WrongPass123") is False


def test_admin_password_werkzeug_hashing_preserved(app):
    """Verify Werkzeug secure cryptographic password hashing is preserved."""
    with app.app_context():
        admin = Admin(username="hash_test", email="hash@example.com")
        admin.set_password("MySecurePass#2026")

        # Verify hash uses Werkzeug format (starts with hashing algorithm prefix)
        assert admin.password_hash.startswith(("scrypt:", "pbkdf2:"))
        # Ensure plaintext password is never stored
        assert "MySecurePass#2026" not in admin.password_hash


def test_create_or_update_admin_password_length_enforcement(app):
    """Test create_or_update_admin helper rejects passwords < 8 characters."""
    with app.app_context():
        # 7 characters rejected
        with pytest.raises(ValueError) as exc:
            create_or_update_admin("newadmin", "newadmin@example.com", "Seven1!")
        assert "at least 8 characters" in str(exc.value)

        # 8 characters accepted
        admin = create_or_update_admin("newadmin", "newadmin@example.com", "Eight123!")
        assert admin.id is not None
        assert admin.check_password("Eight123!") is True


def test_rotate_admin_password_length_enforcement(app):
    """Test rotate_admin_password helper rejects new passwords < 8 characters."""
    with app.app_context():
        admin = Admin(username="rotatetest", email="rotatetest@example.com")
        admin.set_password("InitialStrongPassword123!")
        db.session.add(admin)
        db.session.commit()

        # 7 characters rejected
        with pytest.raises(ValueError) as exc:
            rotate_admin_password("rotatetest", "Fail7!a")
        assert "at least 8 characters" in str(exc.value)

        # 8 characters accepted
        updated = rotate_admin_password("rotatetest", "NewEight123!")
        assert updated.check_password("NewEight123!") is True


# ============================================================================
# TASK 4: Rate Limiting, Proxy IP Resolution & 429 Response Tests
# ============================================================================

def test_admin_login_rate_limiting_triggers_429(app, client):
    """Test admin login endpoint throttles after limit exceeded with 429 and Retry-After header."""
    limiter.reset()

    # Enable rate limiting and configure low threshold for test
    app.config["RATELIMIT_ENABLED"] = True
    app.config["RATELIMIT_ADMIN_LOGIN_LIMIT"] = 3
    app.config["RATELIMIT_ADMIN_LOGIN_PERIOD"] = 60

    try:
        # First 3 attempts: reach endpoint (return 401 Unauthorized for bad creds)
        for _ in range(3):
            res = client.post("/api/admin/login", json={
                "username": "attacker",
                "password": "wrongpassword"
            })
            assert res.status_code == 401

        # 4th attempt: throttled with 429 Too Many Requests
        res4 = client.post("/api/admin/login", json={
            "username": "attacker",
            "password": "wrongpassword"
        })
        assert res4.status_code == 429
        data = res4.get_json()
        assert "Too many requests" in data["error"]
        assert "retry_after" in data
        assert "Retry-After" in res4.headers
        assert int(res4.headers["Retry-After"]) > 0

    finally:
        limiter.reset()
        app.config["RATELIMIT_ENABLED"] = False


def test_order_creation_rate_limiting_triggers_429(app, client):
    """Test order creation endpoint throttles rapid requests with 429 and Retry-After header."""
    limiter.reset()

    # Enable rate limiting and configure low limit for test
    app.config["RATELIMIT_ENABLED"] = True
    app.config["RATELIMIT_ORDER_CREATE_LIMIT"] = 2
    app.config["RATELIMIT_ORDER_CREATE_PERIOD"] = 60

    try:
        # Requests 1 and 2: reach endpoint
        for _ in range(2):
            res = client.post("/api/orders", json={})
            # Malformed request returns 400, but counts against rate limit
            assert res.status_code == 400

        # Request 3: throttled with 429 Too Many Requests
        res3 = client.post("/api/orders", json={})
        assert res3.status_code == 429
        data = res3.get_json()
        assert "Too many requests" in data["error"]
        assert "retry_after" in data
        assert "Retry-After" in res3.headers

    finally:
        limiter.reset()
        app.config["RATELIMIT_ENABLED"] = False


def test_rate_limiting_disabled_by_default_in_tests(app, client):
    """Verify that automated tests can make multiple requests without being throttled."""
    limiter.reset()
    assert app.config.get("RATELIMIT_ENABLED") is False

    # Perform 15 consecutive requests; none should be 429
    for _ in range(15):
        res = client.get("/api/health")
        assert res.status_code == 200


def test_spoofed_forwarded_headers_cannot_bypass_rate_limits(app, client):
    """Verify that varying X-Forwarded-For headers do not bypass rate limits when TRUSTED_PROXIES_COUNT=0."""
    limiter.reset()
    app.config["RATELIMIT_ENABLED"] = True
    app.config["RATELIMIT_ADMIN_LOGIN_LIMIT"] = 3
    app.config["RATELIMIT_ADMIN_LOGIN_PERIOD"] = 60
    app.config["TRUSTED_PROXIES_COUNT"] = 0

    try:
        # Send 3 requests each with a DIFFERENT spoofed X-Forwarded-For header
        for i in range(3):
            res = client.post("/api/admin/login",
                headers={"X-Forwarded-For": f"203.0.113.{i+1}"},
                json={"username": "attacker", "password": "wrongpassword"}
            )
            assert res.status_code == 401

        # 4th request from same client socket (remote_addr='127.0.0.1') with another spoofed header
        res4 = client.post("/api/admin/login",
            headers={"X-Forwarded-For": "198.51.100.99"},
            json={"username": "attacker", "password": "wrongpassword"}
        )
        # Must be rate limited to 429 because remote_addr was used, NOT the spoofed header
        assert res4.status_code == 429
        assert "Too many requests" in res4.get_json()["error"]
    finally:
        limiter.reset()
        app.config["RATELIMIT_ENABLED"] = False


def test_trusted_proxy_resolves_client_ip():
    """Verify that when TRUSTED_PROXIES_COUNT=1, Werkzeug ProxyFix correctly resolves client IP."""
    test_app = create_app("testing")
    test_app.config["TRUSTED_PROXIES_COUNT"] = 1
    from werkzeug.middleware.proxy_fix import ProxyFix
    test_app.wsgi_app = ProxyFix(test_app.wsgi_app, x_for=1)

    captured_ips = []

    @test_app.route("/test-ip")
    def ip_endpoint():
        from flask import request
        captured_ips.append(limiter.get_client_ip())
        return {"ip": limiter.get_client_ip()}

    client = test_app.test_client()
    # Upstream proxy peer is 127.0.0.1; X-Forwarded-For contains original client IP
    res = client.get("/test-ip",
        headers={"X-Forwarded-For": "203.0.113.195"},
        environ_base={"REMOTE_ADDR": "127.0.0.1"}
    )
    assert res.status_code == 200
    assert captured_ips[-1] == "203.0.113.195"


def test_canonical_ratelimit_env_vars_loading(monkeypatch):
    """Verify that all four canonical environment variables are correctly loaded into Config."""
    monkeypatch.setenv("RATELIMIT_ADMIN_LOGIN_LIMIT", "7")
    monkeypatch.setenv("RATELIMIT_ADMIN_LOGIN_PERIOD", "120")
    monkeypatch.setenv("RATELIMIT_ORDER_CREATE_LIMIT", "15")
    monkeypatch.setenv("RATELIMIT_ORDER_CREATE_PERIOD", "90")
    monkeypatch.delenv("RATELIMIT_LOGIN_LIMIT", raising=False)
    monkeypatch.delenv("RATELIMIT_LOGIN_PERIOD", raising=False)
    monkeypatch.delenv("RATELIMIT_ORDER_LIMIT", raising=False)
    monkeypatch.delenv("RATELIMIT_ORDER_PERIOD", raising=False)

    importlib.reload(app.config)
    try:
        cfg = app.config.Config
        assert cfg.RATELIMIT_ADMIN_LOGIN_LIMIT == 7
        assert cfg.RATELIMIT_ADMIN_LOGIN_PERIOD == 120
        assert cfg.RATELIMIT_ORDER_CREATE_LIMIT == 15
        assert cfg.RATELIMIT_ORDER_CREATE_PERIOD == 90
        # Legacy aliases also match canonical values
        assert cfg.RATELIMIT_LOGIN_LIMIT == 7
        assert cfg.RATELIMIT_LOGIN_PERIOD == 120
        assert cfg.RATELIMIT_ORDER_LIMIT == 15
        assert cfg.RATELIMIT_ORDER_PERIOD == 90
        # Inherited by environment configurations
        assert app.config.DevelopmentConfig.RATELIMIT_ADMIN_LOGIN_LIMIT == 7
        assert app.config.ProductionConfig.RATELIMIT_ORDER_CREATE_LIMIT == 15
    finally:
        monkeypatch.undo()
        importlib.reload(app.config)


def test_legacy_ratelimit_env_vars_fallback(monkeypatch):
    """Verify that legacy environment variables are loaded when canonical ones are omitted."""
    monkeypatch.delenv("RATELIMIT_ADMIN_LOGIN_LIMIT", raising=False)
    monkeypatch.delenv("RATELIMIT_ADMIN_LOGIN_PERIOD", raising=False)
    monkeypatch.delenv("RATELIMIT_ORDER_CREATE_LIMIT", raising=False)
    monkeypatch.delenv("RATELIMIT_ORDER_CREATE_PERIOD", raising=False)
    monkeypatch.setenv("RATELIMIT_LOGIN_LIMIT", "8")
    monkeypatch.setenv("RATELIMIT_LOGIN_PERIOD", "45")
    monkeypatch.setenv("RATELIMIT_ORDER_LIMIT", "12")
    monkeypatch.setenv("RATELIMIT_ORDER_PERIOD", "75")

    importlib.reload(app.config)
    try:
        cfg = app.config.Config
        assert cfg.RATELIMIT_ADMIN_LOGIN_LIMIT == 8
        assert cfg.RATELIMIT_ADMIN_LOGIN_PERIOD == 45
        assert cfg.RATELIMIT_ORDER_CREATE_LIMIT == 12
        assert cfg.RATELIMIT_ORDER_CREATE_PERIOD == 75
        assert cfg.RATELIMIT_LOGIN_LIMIT == 8
        assert cfg.RATELIMIT_LOGIN_PERIOD == 45
        assert cfg.RATELIMIT_ORDER_LIMIT == 12
        assert cfg.RATELIMIT_ORDER_PERIOD == 75
    finally:
        monkeypatch.undo()
        importlib.reload(app.config)


def test_canonical_ratelimit_env_vars_precedence_over_legacy(monkeypatch):
    """Verify that canonical environment variables take strict precedence when both exist."""
    monkeypatch.setenv("RATELIMIT_ADMIN_LOGIN_LIMIT", "14")
    monkeypatch.setenv("RATELIMIT_ADMIN_LOGIN_PERIOD", "100")
    monkeypatch.setenv("RATELIMIT_ORDER_CREATE_LIMIT", "25")
    monkeypatch.setenv("RATELIMIT_ORDER_CREATE_PERIOD", "80")
    monkeypatch.setenv("RATELIMIT_LOGIN_LIMIT", "3")
    monkeypatch.setenv("RATELIMIT_LOGIN_PERIOD", "30")
    monkeypatch.setenv("RATELIMIT_ORDER_LIMIT", "4")
    monkeypatch.setenv("RATELIMIT_ORDER_PERIOD", "40")

    importlib.reload(app.config)
    try:
        cfg = app.config.Config
        assert cfg.RATELIMIT_ADMIN_LOGIN_LIMIT == 14
        assert cfg.RATELIMIT_ADMIN_LOGIN_PERIOD == 100
        assert cfg.RATELIMIT_ORDER_CREATE_LIMIT == 25
        assert cfg.RATELIMIT_ORDER_CREATE_PERIOD == 80
        assert cfg.RATELIMIT_LOGIN_LIMIT == 14
        assert cfg.RATELIMIT_LOGIN_PERIOD == 100
        assert cfg.RATELIMIT_ORDER_LIMIT == 25
        assert cfg.RATELIMIT_ORDER_PERIOD == 80
    finally:
        monkeypatch.undo()
        importlib.reload(app.config)


def test_runtime_legacy_flask_config_fallback(app, client):
    """Verify runtime rate limiter honors legacy Flask config keys when canonical keys are absent."""
    limiter.reset()
    app.config["RATELIMIT_ENABLED"] = True

    # Strip canonical keys to test fallback
    app.config.pop("RATELIMIT_ADMIN_LOGIN_LIMIT", None)
    app.config.pop("RATELIMIT_ADMIN_LOGIN_PERIOD", None)
    app.config.pop("RATELIMIT_ORDER_CREATE_LIMIT", None)
    app.config.pop("RATELIMIT_ORDER_CREATE_PERIOD", None)

    # Set legacy config keys
    app.config["RATELIMIT_LOGIN_LIMIT"] = 2
    app.config["RATELIMIT_LOGIN_PERIOD"] = 60
    app.config["RATELIMIT_ORDER_LIMIT"] = 2
    app.config["RATELIMIT_ORDER_PERIOD"] = 60

    try:
        # Admin login fallback: 2 attempts succeed (401), 3rd is throttled (429)
        for _ in range(2):
            res = client.post("/api/admin/login", json={"username": "u", "password": "p"})
            assert res.status_code == 401
        res3 = client.post("/api/admin/login", json={"username": "u", "password": "p"})
        assert res3.status_code == 429
        assert "Limit of 2 requests per 60s exceeded" in res3.get_json()["error"]

        limiter.reset()

        # Order creation fallback: 2 requests reach endpoint (400), 3rd is throttled (429)
        for _ in range(2):
            res = client.post("/api/orders", json={})
            assert res.status_code == 400
        res_order = client.post("/api/orders", json={})
        assert res_order.status_code == 429
        assert "Limit of 2 requests per 60s exceeded" in res_order.get_json()["error"]
    finally:
        limiter.reset()
        app.config["RATELIMIT_ENABLED"] = False
        app.config.pop("RATELIMIT_LOGIN_LIMIT", None)
        app.config.pop("RATELIMIT_LOGIN_PERIOD", None)
        app.config.pop("RATELIMIT_ORDER_LIMIT", None)
        app.config.pop("RATELIMIT_ORDER_PERIOD", None)


def test_rate_limiting_default_limits_enforced_when_overrides_absent(app, client):
    """Verify default limits of 5 (admin login) and 10 (order create) per 60s when config overrides are absent."""
    limiter.reset()
    app.config["RATELIMIT_ENABLED"] = True

    for key in (
        "RATELIMIT_ADMIN_LOGIN_LIMIT",
        "RATELIMIT_ADMIN_LOGIN_PERIOD",
        "RATELIMIT_LOGIN_LIMIT",
        "RATELIMIT_LOGIN_PERIOD",
        "RATELIMIT_ORDER_CREATE_LIMIT",
        "RATELIMIT_ORDER_CREATE_PERIOD",
        "RATELIMIT_ORDER_LIMIT",
        "RATELIMIT_ORDER_PERIOD",
    ):
        app.config.pop(key, None)

    try:
        # Admin login: 5 allowed, 6th triggers 429
        for _ in range(5):
            res = client.post("/api/admin/login", json={"username": "u", "password": "p"})
            assert res.status_code == 401
        res6 = client.post("/api/admin/login", json={"username": "u", "password": "p"})
        assert res6.status_code == 429
        assert "Limit of 5 requests per 60s exceeded" in res6.get_json()["error"]
        assert int(res6.headers["Retry-After"]) > 0

        limiter.reset()

        # Order creation: 10 allowed, 11th triggers 429
        for _ in range(10):
            res = client.post("/api/orders", json={})
            assert res.status_code == 400
        res11 = client.post("/api/orders", json={})
        assert res11.status_code == 429
        assert "Limit of 10 requests per 60s exceeded" in res11.get_json()["error"]
        assert int(res11.headers["Retry-After"]) > 0
    finally:
        limiter.reset()
        app.config["RATELIMIT_ENABLED"] = False


def test_rate_limiting_sliding_window_expiry_with_time_mock(app, client, monkeypatch):
    """Verify requests are permitted again after sliding window period expires using mocked monotonic time."""
    limiter.reset()
    app.config["RATELIMIT_ENABLED"] = True
    app.config["RATELIMIT_ADMIN_LOGIN_LIMIT"] = 2
    app.config["RATELIMIT_ADMIN_LOGIN_PERIOD"] = 60

    current_simulated_time = 1000.0

    monkeypatch.setattr("app.services.rate_limiter.time.monotonic", lambda: current_simulated_time)

    try:
        # Requests 1 and 2 at t=1000.0: allowed
        res1 = client.post("/api/admin/login", json={"username": "u", "password": "p"})
        assert res1.status_code == 401
        res2 = client.post("/api/admin/login", json={"username": "u", "password": "p"})
        assert res2.status_code == 401

        # Request 3 at t=1000.0: throttled (429)
        res3 = client.post("/api/admin/login", json={"username": "u", "password": "p"})
        assert res3.status_code == 429
        assert int(res3.headers["Retry-After"]) == 61

        # Advance by 30s (t=1030.0, still within 60s window): still throttled
        current_simulated_time = 1030.0
        res4 = client.post("/api/admin/login", json={"username": "u", "password": "p"})
        assert res4.status_code == 429

        # Advance past 60s window (t=1061.0): t=1000.0 timestamps have expired
        current_simulated_time = 1061.0
        res5 = client.post("/api/admin/login", json={"username": "u", "password": "p"})
        assert res5.status_code == 401
    finally:
        limiter.reset()
        app.config["RATELIMIT_ENABLED"] = False


def test_explicit_limiter_reset_restores_allowance_after_throttling(app, client):
    """Verify that calling limiter.reset() immediately restores request allowance after throttling."""
    limiter.reset()
    app.config["RATELIMIT_ENABLED"] = True
    app.config["RATELIMIT_ADMIN_LOGIN_LIMIT"] = 2
    app.config["RATELIMIT_ADMIN_LOGIN_PERIOD"] = 60

    try:
        # Exhaust limit
        client.post("/api/admin/login", json={"username": "u", "password": "p"})
        client.post("/api/admin/login", json={"username": "u", "password": "p"})

        # Confirm throttled
        res_throttled = client.post("/api/admin/login", json={"username": "u", "password": "p"})
        assert res_throttled.status_code == 429

        # Explicitly reset limiter
        limiter.reset()

        # Immediate next request should succeed and reach endpoint
        res_unblocked = client.post("/api/admin/login", json={"username": "u", "password": "p"})
        assert res_unblocked.status_code == 401
    finally:
        limiter.reset()
        app.config["RATELIMIT_ENABLED"] = False


# ============================================================================
# TASK 5: Admin Token 2-Hour Lifetime Enforcement Tests
# ============================================================================

def test_admin_token_lifetime_reduced_to_2_hours(app, admin_user):
    """Verify that admin tokens use a 2-hour (7200s) default expiration."""
    assert DEFAULT_MAX_AGE_SECONDS == 7200

    with app.app_context():
        admin = db.session.get(Admin, admin_user)
        token = AuthService.generate_token(admin)

        # Valid within 2 hours
        assert AuthService.verify_token(token, max_age=7200) is not None

        # Expired if simulated time elapsed exceeds 2 hours
        assert AuthService.verify_token(token, max_age=-1) is None


# ============================================================================
# PHASE 12 STEP 3B: Admin HttpOnly Cookie & CSRF Protection Tests
# ============================================================================

def test_admin_login_sets_httponly_cookie(client, admin_user):
    """Test successful administrator login sets secure HttpOnly cookie and does not expose token in body."""
    res = client.post("/api/admin/login", json={
        "username": "sec_test_admin",
        "password": "AdminSecurePass123!"
    })
    assert res.status_code == 200
    data = res.get_json()

    # 1. Token must NOT be in JSON response
    assert "token" not in data
    assert "csrf_token" in data
    assert "successful" in data["message"].lower()
    assert data["admin"]["username"] == "sec_test_admin"

    # 2. Check Set-Cookie headers
    all_cookies = "".join(res.headers.getlist("Set-Cookie"))
    assert "admin_session=" in all_cookies
    assert "HttpOnly" in all_cookies
    assert "SameSite=Strict" in all_cookies
    assert "Path=/api/admin" in all_cookies
    assert "Max-Age=7200" in all_cookies

    # 3. csrf_token cookie also set and readable by script (no HttpOnly on csrf_token cookie)
    assert "csrf_token=" in all_cookies


def test_protected_admin_endpoint_accepts_valid_cookie(client, admin_user):
    """Test GET /api/admin/me works seamlessly with admin_session cookie."""
    login_res = client.post("/api/admin/login", json={
        "username": "sec_test_admin",
        "password": "AdminSecurePass123!"
    })
    assert login_res.status_code == 200

    # Test client automatically transmits cookies
    res = client.get("/api/admin/me")
    assert res.status_code == 200
    assert res.get_json()["admin"]["username"] == "sec_test_admin"


def test_cookie_auth_state_changing_missing_csrf_rejected(client, admin_user):
    """Test state-changing requests using cookie auth without X-CSRF-Token are rejected with 403."""
    client.post("/api/admin/login", json={
        "username": "sec_test_admin",
        "password": "AdminSecurePass123!"
    })

    # Attempt state-changing POST without X-CSRF-Token header
    res = client.post("/api/admin/products",
        headers={"Origin": "http://localhost:5173"},
        json={
            "name": "CSRF Test Product",
            "price": 999.0,
            "category": "Electronics",
            "stock_quantity": 10,
            "description": "Test"
        }
    )
    assert res.status_code == 403
    assert "Missing X-CSRF-Token" in res.get_json()["error"]


def test_cookie_auth_state_changing_invalid_csrf_rejected(client, admin_user):
    """Test state-changing requests using cookie auth with invalid X-CSRF-Token are rejected with 403."""
    client.post("/api/admin/login", json={
        "username": "sec_test_admin",
        "password": "AdminSecurePass123!"
    })

    res = client.post("/api/admin/products",
        headers={
            "Origin": "http://localhost:5173",
            "X-CSRF-Token": "completely-invalid-csrf-token"
        },
        json={
            "name": "CSRF Test Product",
            "price": 999.0,
            "category": "Electronics",
            "stock_quantity": 10,
            "description": "Test"
        }
    )
    assert res.status_code == 403
    assert "Invalid or expired CSRF token" in res.get_json()["error"]


def test_cookie_auth_state_changing_untrusted_origin_rejected(client, admin_user, app):
    """Test state-changing requests using cookie auth from an untrusted origin are rejected with 403."""
    app.config["CORS_ORIGINS"] = "http://localhost:5173"
    try:
        login_res = client.post("/api/admin/login", json={
            "username": "sec_test_admin",
            "password": "AdminSecurePass123!"
        })
        csrf_token = login_res.get_json()["csrf_token"]

        res = client.post("/api/admin/products",
            headers={
                "Origin": "https://malicious-attacker.com",
                "X-CSRF-Token": csrf_token
            },
            json={
                "name": "CSRF Test Product",
                "price": 999.0,
                "category": "Electronics",
                "stock_quantity": 10,
                "description": "Test"
            }
        )
        assert res.status_code == 403
        assert "untrusted origin" in res.get_json()["error"].lower()
    finally:
        app.config["CORS_ORIGINS"] = "*"


def test_cookie_auth_state_changing_valid_csrf_accepted(client, admin_user):
    """Test state-changing requests using cookie auth with valid CSRF token and origin succeed."""
    login_res = client.post("/api/admin/login", json={
        "username": "sec_test_admin",
        "password": "AdminSecurePass123!"
    })
    csrf_token = login_res.get_json()["csrf_token"]

    res = client.post("/api/admin/products",
        headers={
            "Origin": "http://localhost:5173",
            "X-CSRF-Token": csrf_token
        },
        json={
            "name": "Valid CSRF Product",
            "price": 1499.0,
            "category": "Accessories",
            "stock_quantity": 5,
            "description": "Legitimate product creation"
        }
    )
    assert res.status_code == 201
    assert res.get_json()["product"]["name"] == "Valid CSRF Product"


def test_admin_logout_revokes_token_and_clears_cookie(client, admin_user, app):
    """Test logout revokes token in DB, clears cookie, and invalidates session."""
    from app.models.revoked_token import RevokedToken

    login_res = client.post("/api/admin/login", json={
        "username": "sec_test_admin",
        "password": "AdminSecurePass123!"
    })
    csrf_token = login_res.get_json()["csrf_token"]

    # Logout
    logout_res = client.post("/api/admin/logout",
        headers={
            "Origin": "http://localhost:5173",
            "X-CSRF-Token": csrf_token
        }
    )
    assert logout_res.status_code == 200
    assert "logged out" in logout_res.get_json()["message"].lower()

    # Set-Cookie clears admin_session with matching path and SameSite=Strict
    all_cookies = "".join(logout_res.headers.getlist("Set-Cookie"))
    assert "admin_session=" in all_cookies
    assert "Max-Age=0" in all_cookies or "expires=Thu, 01 Jan 1970" in all_cookies
    assert "SameSite=Strict" in all_cookies
    assert "Path=/api/admin" in all_cookies

    # RevokedToken entry exists in database
    with app.app_context():
        revoked_count = RevokedToken.query.count()
        assert revoked_count >= 1

    # Attempting to access protected endpoint fails
    res_me = client.get("/api/admin/me")
    assert res_me.status_code == 401


def test_revoked_token_cannot_be_reused(client, admin_user, app):
    """Test that a revoked token cannot be reused even if provided via Authorization Bearer header."""
    with app.app_context():
        admin = db.session.get(Admin, admin_user)
        token = AuthService.generate_token(admin)
        AuthService.revoke_token(token)

    # Calling /api/admin/me with revoked token
    res = client.get("/api/admin/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert "revoked" in res.get_json()["error"].lower() or "invalid" in res.get_json()["error"].lower()


def test_storefront_orders_unaffected_by_csrf(client, app):
    """Test customer storefront order placement does not require CSRF token or admin session."""
    from app.database import seed_db
    with app.app_context():
        seed_db()

    res = client.post("/api/orders", json={
        "customer_name": "Test Customer",
        "customer_email": "customer@example.com",
        "customer_phone": "9876543210",
        "delivery_address": "123 Test Street",
        "city": "Mumbai",
        "postal_code": "400001",
        "items": [{"product_id": 1, "quantity": 1}]
    })
    assert res.status_code == 201
    assert "order" in res.get_json()
    assert res.get_json()["order"]["currency"] == "INR"
