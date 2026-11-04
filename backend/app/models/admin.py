from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.db import db


MIN_ADMIN_PASSWORD_LENGTH = 8


class Admin(db.Model):
    """Administrator user model for dashboard authentication and authorization."""
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="admin")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    last_login_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def set_password(self, password: str) -> None:
        """Hash and store password using Werkzeug cryptographic hashing."""
        if not password or len(password) < MIN_ADMIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_ADMIN_PASSWORD_LENGTH} characters long.")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify candidate password against the stored password hash."""
        if not self.password_hash or not password:
            return False
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """Serialize admin record safely, strictly omitting the password hash."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Admin id={self.id} username='{self.username}' role='{self.role}'>"
