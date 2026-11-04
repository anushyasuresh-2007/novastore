import os
import pytest
from app import create_app
from app.models.db import db
from app.models.admin import Admin
from app.services.rate_limiter import limiter
from create_admin import create_or_update_admin
from rotate_admin_password import rotate_admin_password


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


def test_production_valid_secret_key_accepted(monkeypatch):
    """Test application startup succeeds in production with a unique valid SECRET_KEY."""
    safe_key = "a9f8b2c4e6d871350a4bf39801ec6d4352ab908e7f1234567890abcdef123456"
    monkeypatch.setenv("SECRET_KEY", safe_key)
    monkeypatch.setenv("CORS_ORIGINS", "https://novastore-example.com")

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

    prod_app = create_app("production")
    client = prod_app.test_client()

    # Request from allowed origin
    res = client.get("/api/health", headers={"Origin": "https://store.example.com"})
    assert res.status_code == 200
    assert res.headers.get("Access-Control-Allow-Origin") == "https://store.example.com"
    assert res.headers.get("Access-Control-Allow-Credentials") == "true"


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
# TASK 4: Rate Limiting & 429 Response Tests
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
