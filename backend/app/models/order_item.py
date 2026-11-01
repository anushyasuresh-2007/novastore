from sqlalchemy import CheckConstraint
from app.models.db import db


class OrderItem(db.Model):
    """OrderItem model storing snapshot of purchased products within an order."""
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    product_name = db.Column(db.String(150), nullable=False)  # Purchase-time snapshot
    unit_price = db.Column(db.Float, nullable=False)  # Purchase-time snapshot
    quantity = db.Column(db.Integer, nullable=False)
    line_total = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="INR")

    product = db.relationship("Product", lazy="joined")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_order_item_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="check_order_item_unit_price_non_negative"),
        CheckConstraint("line_total >= 0", name="check_order_item_line_total_non_negative"),
    )

    def to_dict(self) -> dict:
        """Convert order item to dictionary format for JSON responses."""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "unit_price": round(float(self.unit_price), 2),
            "quantity": int(self.quantity),
            "line_total": round(float(self.line_total), 2),
            "currency": self.currency or "INR",
        }

    def __repr__(self) -> str:
        return f"<OrderItem id={self.id} order_id={self.order_id} product='{self.product_name}' qty={self.quantity}>"
