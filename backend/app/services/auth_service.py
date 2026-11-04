"""Authentication service for administrator login, session tokens, and access control."""
from functools import wraps
from datetime import datetime, timezone, timedelta
import hashlib
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import request, jsonify, current_app
from app.models.db import db
from app.models.admin import Admin
from app.models.revoked_token import RevokedToken

TOKEN_SALT = "novastore-admin-auth-salt"
CSRF_SALT = "novastore-admin-csrf-salt"
DEFAULT_MAX_AGE_SECONDS = 7200  # 2 hours validity (hardened session lifetime)


class AuthService:
    """Service handling administrator authentication tokens, password verification, and CSRF protection."""

    @classmethod
    def _get_serializer(cls) -> URLSafeTimedSerializer:
        """Create URLSafeTimedSerializer using application secret key."""
        secret_key = current_app.config.get("SECRET_KEY", "dev-secret-key-change-in-production")
        return URLSafeTimedSerializer(secret_key=secret_key, salt=TOKEN_SALT)

    @classmethod
    def _get_csrf_serializer(cls) -> URLSafeTimedSerializer:
        """Create URLSafeTimedSerializer for synchronizer CSRF tokens."""
        secret_key = current_app.config.get("SECRET_KEY", "dev-secret-key-change-in-production")
        return URLSafeTimedSerializer(secret_key=secret_key, salt=CSRF_SALT)

    @classmethod
    def _compute_pw_sig(cls, admin: Admin) -> str:
        """Compute a 16-char SHA-256 fingerprint of the current password hash."""
        if not admin or not admin.password_hash:
            return ""
        return hashlib.sha256(admin.password_hash.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def compute_token_sig(cls, token: str) -> str:
        """Compute a 64-character SHA-256 one-way digest of a session token for revocation tracking."""
        if not token:
            return ""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @classmethod
    def generate_token(cls, admin: Admin) -> str:
        """Generate a cryptographically signed, timestamped authentication token."""
        serializer = cls._get_serializer()
        payload = {
            "admin_id": admin.id,
            "username": admin.username,
            "role": admin.role,
            "pw_sig": cls._compute_pw_sig(admin),
        }
        return serializer.dumps(payload)

    @classmethod
    def generate_csrf_token(cls, admin: Admin) -> str:
        """Generate a cryptographically signed synchronizer CSRF token bound to the administrator session."""
        serializer = cls._get_csrf_serializer()
        payload = {
            "admin_id": admin.id,
            "pw_sig": cls._compute_pw_sig(admin),
        }
        return serializer.dumps(payload)

    @classmethod
    def verify_csrf_token(cls, csrf_token: str, admin: Admin, max_age: int = DEFAULT_MAX_AGE_SECONDS) -> bool:
        """Verify the signature, expiry, and admin/session binding of a CSRF token."""
        if not csrf_token or not admin:
            return False

        serializer = cls._get_csrf_serializer()
        try:
            payload = serializer.loads(csrf_token, max_age=max_age)
            if payload.get("admin_id") != admin.id:
                return False
            if payload.get("pw_sig") != cls._compute_pw_sig(admin):
                return False
            return True
        except (BadSignature, SignatureExpired):
            return False

    @classmethod
    def revoke_token(cls, token: str, max_age: int = DEFAULT_MAX_AGE_SECONDS):
        """Add a token's SHA-256 signature to the persistent database revocation blocklist."""
        if not token:
            return
        token_sig = cls.compute_token_sig(token)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=max_age)
        RevokedToken.revoke(token_sig, expires_at)
        RevokedToken.cleanup_expired()

    @classmethod
    def verify_token(cls, token: str, max_age: int = DEFAULT_MAX_AGE_SECONDS) -> Admin | None:
        """
        Verify the validity and signature of an authentication token.
        Returns the Admin instance if valid, active, unrevoked, and matches current password state,
        or None if expired, tampered, revoked via logout/password change, or deactivated.
        """
        if not token:
            return None

        # Check server-side persistent revocation blocklist
        token_sig = cls.compute_token_sig(token)
        if RevokedToken.is_revoked(token_sig):
            return None

        serializer = cls._get_serializer()
        try:
            payload = serializer.loads(token, max_age=max_age)
            admin_id = payload.get("admin_id")
            if not admin_id:
                return None

            admin = db.session.get(Admin, admin_id)
            if not admin or not admin.is_active:
                return None

            # Invalidate tokens issued prior to an administrator password rotation
            pw_sig = payload.get("pw_sig")
            if pw_sig and cls._compute_pw_sig(admin) != pw_sig:
                return None

            return admin
        except (BadSignature, SignatureExpired):
            return None

    @classmethod
    def authenticate(cls, identifier: str, password: str) -> Admin | None:
        """
        Authenticate an administrator by username or email and password.
        Updates last_login_at timestamp upon success.
        """
        if not identifier or not password:
            return None

        clean_id = identifier.strip().lower()
        admin = Admin.query.filter(
            (Admin.username.ilike(clean_id)) | (Admin.email.ilike(clean_id))
        ).first()

        if not admin or not admin.is_active:
            return None

        if not admin.check_password(password):
            return None

        # Update last login timestamp
        admin.last_login_at = datetime.now(timezone.utc)
        db.session.commit()
        return admin

    @classmethod
    def is_trusted_origin(cls, origin: str) -> bool:
        """Check if an Origin or Referer header matches the configured CORS origins."""
        if not origin:
            return False

        cors_config = current_app.config.get("CORS_ORIGINS", "*")
        if cors_config == "*":
            return True

        if isinstance(cors_config, str):
            allowed = [o.strip().rstrip("/") for o in cors_config.split(",") if o.strip()]
        elif isinstance(cors_config, (list, tuple, set)):
            allowed = [str(o).strip().rstrip("/") for o in cors_config if str(o).strip()]
        else:
            allowed = [str(cors_config).strip().rstrip("/")]

        clean_origin = origin.strip().rstrip("/")
        return clean_origin in allowed


def get_request_auth() -> tuple[str | None, str]:
    """
    Extract authentication token and source from the active request context.
    Priority:
    1. HttpOnly cookie 'admin_session' (source: 'cookie')
    2. Authorization Bearer header (source: 'header')
    3. Custom X-Admin-Token header (source: 'header')
    """
    cookie_token = request.cookies.get("admin_session")
    if cookie_token:
        return cookie_token, "cookie"

    auth_header = request.headers.get("Authorization")
    if auth_header:
        parts = auth_header.split(" ")
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip(), "header"

    custom_header = request.headers.get("X-Admin-Token")
    if custom_header:
        return custom_header.strip(), "header"

    return None, "none"


def admin_required(f):
    """
    Decorator to protect administrator endpoints.
    Supports HttpOnly cookie 'admin_session' or Authorization bearer header.
    Enforces server-side CSRF validation (Origin check and Synchronizer token) on
    state-changing requests (POST, PUT, PATCH, DELETE) when authenticated via cookie.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token, auth_source = get_request_auth()

        if not token:
            return jsonify({
                "error": "Authentication required. Please log in as an administrator."
            }), 401

        admin = AuthService.verify_token(token)
        if not admin:
            return jsonify({
                "error": "Invalid, expired, or revoked administrator session. Please log in again."
            }), 401

        if not admin.is_active:
            return jsonify({
                "error": "Administrator account is inactive. Access forbidden."
            }), 403

        # CSRF Protection: enforce on cookie-authenticated state-changing requests
        if auth_source == "cookie" and request.method in ("POST", "PUT", "PATCH", "DELETE"):
            # 1. Validate Origin / Referer against configured allowed origins
            origin = request.headers.get("Origin")
            if origin:
                if not AuthService.is_trusted_origin(origin):
                    return jsonify({
                        "error": "CSRF verification failed: Untrusted Origin header."
                    }), 403
            elif request.headers.get("Referer"):
                from urllib.parse import urlparse
                ref = request.headers.get("Referer")
                parsed_ref = urlparse(ref)
                ref_origin = f"{parsed_ref.scheme}://{parsed_ref.netloc}"
                if not AuthService.is_trusted_origin(ref_origin):
                    return jsonify({
                        "error": "CSRF verification failed: Untrusted Referer header."
                    }), 403

            # 2. Validate Synchronizer CSRF Token
            csrf_token = request.headers.get("X-CSRF-Token")
            if not csrf_token:
                return jsonify({
                    "error": "CSRF verification failed: Missing X-CSRF-Token header."
                }), 403

            if not AuthService.verify_csrf_token(csrf_token, admin):
                return jsonify({
                    "error": "CSRF verification failed: Invalid or expired CSRF token."
                }), 403

        # Attach authenticated admin, token, and auth source to request context
        request.current_admin = admin
        request.token = token
        request.auth_source = auth_source
        return f(*args, **kwargs)

    return decorated_function
