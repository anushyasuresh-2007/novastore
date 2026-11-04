from datetime import datetime, timezone
from app.models.db import db


class RevokedToken(db.Model):
    """
    Stores one-way cryptographic SHA-256 signatures of revoked administrator tokens.
    Raw session tokens are never stored to preserve confidentiality even if database is inspected.
    """
    __tablename__ = "revoked_tokens"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    token_sig = db.Column(db.String(64), unique=True, nullable=False, index=True)
    revoked_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    expires_at = db.Column(db.DateTime, nullable=False, index=True)

    @classmethod
    def is_revoked(cls, token_sig: str) -> bool:
        """Check if a token signature exists in the revocation blocklist."""
        if not token_sig:
            return False
        return db.session.query(cls.id).filter_by(token_sig=token_sig).first() is not None

    @classmethod
    def revoke(cls, token_sig: str, expires_at: datetime) -> "RevokedToken":
        """Persist a revoked token signature."""
        if not token_sig:
            raise ValueError("Token signature is required for revocation.")
        # Check if already revoked
        existing = cls.query.filter_by(token_sig=token_sig).first()
        if existing:
            return existing

        revocation = cls(token_sig=token_sig, expires_at=expires_at)
        db.session.add(revocation)
        db.session.commit()
        return revocation

    @classmethod
    def cleanup_expired(cls) -> int:
        """Purge expired revocation records safely to keep table size bounded."""
        now = datetime.now(timezone.utc)
        deleted = cls.query.filter(cls.expires_at < now).delete()
        if deleted > 0:
            db.session.commit()
        return deleted

    def __repr__(self) -> str:
        return f"<RevokedToken sig='{self.token_sig[:12]}...' expires='{self.expires_at}'>"
