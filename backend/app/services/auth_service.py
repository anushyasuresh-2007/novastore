"""Authentication service for administrator login, session tokens, and access control."""
from functools import wraps
from datetime import datetime, timezone
import hashlib
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import request, jsonify, current_app
from app.models.db import db
from app.models.admin import Admin

TOKEN_SALT = "novastore-admin-auth-salt"
DEFAULT_MAX_AGE_SECONDS = 86400  # 24 hours validity


class AuthService:
    """Service handling administrator authentication tokens and password verification."""

    @classmethod
    def _get_serializer(cls) -> URLSafeTimedSerializer:
        """Create URLSafeTimedSerializer using application secret key."""
        secret_key = current_app.config.get("SECRET_KEY", "dev-secret-key-change-in-production")
        return URLSafeTimedSerializer(secret_key=secret_key, salt=TOKEN_SALT)

    @classmethod
    def _compute_pw_sig(cls, admin: Admin) -> str:
        """Compute a 16-char SHA-256 fingerprint of the current password hash."""
        if not admin or not admin.password_hash:
            return ""
        return hashlib.sha256(admin.password_hash.encode("utf-8")).hexdigest()[:16]

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
    def verify_token(cls, token: str, max_age: int = DEFAULT_MAX_AGE_SECONDS) -> Admin | None:
        """
        Verify the validity and signature of an authentication token.
        Returns the Admin instance if valid, active, and token matches current password state,
        or None if expired, tampered, deactivated, or revoked via password change.
        """
        if not token:
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


def admin_required(f):
    """
    Decorator to protect administrator endpoints.
    Requires a valid signed bearer token in Authorization header or X-Admin-Token header.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        token = None

        if auth_header:
            parts = auth_header.split(" ")
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1].strip()

        # Fallback to custom header if Authorization header not provided
        if not token:
            token = request.headers.get("X-Admin-Token")

        if not token:
            return jsonify({
                "error": "Authentication required. Please provide a valid administrator token."
            }), 401

        admin = AuthService.verify_token(token)
        if not admin:
            return jsonify({
                "error": "Invalid or expired administrator token. Please log in again."
            }), 401

        if not admin.is_active:
            return jsonify({
                "error": "Administrator account is inactive. Access forbidden."
            }), 403

        # Attach authenticated admin to request context
        request.current_admin = admin
        return f(*args, **kwargs)

    return decorated_function
