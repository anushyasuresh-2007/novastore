from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, Index
from app.models.db import db


class Order(db.Model):
    """Order model storing customer checkout information and overall order details."""
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_reference = db.Column(db.String(36), unique=True, nullable=False, index=True)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False, index=True)
    customer_phone = db.Column(db.String(30), nullable=False)
    delivery_address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(20), nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    delivery_fee = db.Column(db.Float, nullable=False, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="INR")
    status = db.Column(db.String(30), nullable=False, default="CONFIRMED", index=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    items = db.relationship(
        "OrderItem",
        backref="order",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint("subtotal >= 0", name="check_order_subtotal_non_negative"),
        CheckConstraint("delivery_fee >= 0", name="check_order_delivery_fee_non_negative"),
        CheckConstraint("total_amount >= 0", name="check_order_total_amount_non_negative"),
        Index("idx_orders_email_created", "customer_email", "created_at"),
    )

    def to_dict(self, include_items: bool = True) -> dict:
        """Convert order to dictionary format for JSON responses."""
        data = {
            "id": self.id,
            "order_reference": self.order_reference,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "customer_phone": self.customer_phone,
            "delivery_address": self.delivery_address,
            "city": self.city,
            "postal_code": self.postal_code,
            "subtotal": round(float(self.subtotal), 2),
            "delivery_fee": round(float(self.delivery_fee), 2),
            "total_amount": round(float(self.total_amount), 2),
            "currency": self.currency or "INR",
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_items:
            data["items"] = [item.to_dict() for item in self.items]
        return data

    def __repr__(self) -> str:
        return f"<Order id={self.id} ref='{self.order_reference}' total={self.total_amount} status='{self.status}'>"
