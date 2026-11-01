import re
import secrets
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional
from app.models.db import db
from app.models.product import Product
from app.models.order import Order
from app.models.order_item import OrderItem


class OrderValidationError(Exception):
    """Custom exception raised when customer or cart order input is invalid."""
    pass


class InsufficientStockError(Exception):
    """Custom exception raised when product stock is inadequate for the order."""
    pass


class OrderService:
    """Service handling order creation, stock verification, and calculation."""

    EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    # Indian phone format: optional +91 or 0, followed by 10 digits starting with 6-9
    PHONE_REGEX = re.compile(r"^(?:\+91[\-\s]?)?[6-9]\d{9}$")
    # Indian PIN / postal code: exactly 6 digits
    POSTAL_REGEX = re.compile(r"^\d{6}$")

    @classmethod
    def validate_customer_details(cls, data: Dict[str, Any]) -> None:
        """Validate all required customer contact and delivery fields."""
        name = str(data.get("customer_name", "")).strip()
        email = str(data.get("customer_email", "")).strip()
        phone = str(data.get("customer_phone", "")).strip()
        address = str(data.get("delivery_address", "")).strip()
        city = str(data.get("city", "")).strip()
        postal_code = str(data.get("postal_code", "")).strip()

        if not name or len(name) < 2:
            raise OrderValidationError("Full name is required (at least 2 characters).")
        if len(name) > 120:
            raise OrderValidationError("Full name cannot exceed 120 characters.")

        if not email or not cls.EMAIL_REGEX.match(email):
            raise OrderValidationError("A valid email address is required (e.g. name@example.com).")

        # Normalize phone: remove spaces and hyphens
        clean_phone = re.sub(r"[\s\-]", "", phone)
        if not clean_phone or not cls.PHONE_REGEX.match(clean_phone):
            raise OrderValidationError("Please provide a valid 10-digit mobile number (e.g. 9876543210 or +919876543210).")

        if not address or len(address) < 5:
            raise OrderValidationError("Delivery address is required (at least 5 characters).")
        if len(address) > 255:
            raise OrderValidationError("Delivery address cannot exceed 255 characters.")

        if not city or len(city) < 2:
            raise OrderValidationError("City is required (at least 2 characters).")
        if len(city) > 100:
            raise OrderValidationError("City cannot exceed 100 characters.")

        if not postal_code or not cls.POSTAL_REGEX.match(postal_code):
            raise OrderValidationError("Please enter a valid 6-digit postal code (PIN code).")

    @classmethod
    def generate_unique_order_reference(cls) -> str:
        """Generate a unique order reference in the format ORD-YYYYMMDD-XXXX."""
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        for _ in range(10):
            # 8 uppercase alphanumeric characters for high entropy uniqueness
            suffix = secrets.token_hex(4).upper()
            reference = f"ORD-{date_str}-{suffix}"
            if not Order.query.filter_by(order_reference=reference).first():
                return reference
        # Fallback to longer token if collision
        return f"ORD-{date_str}-{secrets.token_hex(4).upper()}"

    @classmethod
    def create_order(cls, payload: Dict[str, Any]) -> Order:
        """
        Validate order, check database product prices and stock, calculate totals,
        deduct stock, and save order within a database transaction.
        """
        if not isinstance(payload, dict):
            raise OrderValidationError("Invalid request payload.")

        # 1. Validate customer details
        cls.validate_customer_details(payload)

        # 2. Validate items array
        raw_items = payload.get("items")
        if not raw_items or not isinstance(raw_items, list) or len(raw_items) == 0:
            raise OrderValidationError("Order must contain at least one product item.")

        # Aggregate quantities by product_id in case client sent duplicates
        item_quantities: Dict[int, int] = {}
        for idx, item in enumerate(raw_items):
            if not isinstance(item, dict):
                raise OrderValidationError(f"Item #{idx + 1} must be a valid JSON object.")

            product_id = item.get("product_id")
            if product_id is None or not isinstance(product_id, int) or product_id <= 0:
                raise OrderValidationError(f"Item #{idx + 1} contains an invalid product_id.")

            quantity = item.get("quantity")
            if quantity is None or not isinstance(quantity, int) or quantity <= 0:
                raise OrderValidationError(f"Quantity for product #{product_id} must be a positive integer.")

            item_quantities[product_id] = item_quantities.get(product_id, 0) + quantity

        # 3. Retrieve products from database using server-side source of truth
        product_ids = list(item_quantities.keys())
        products = Product.query.filter(Product.id.in_(product_ids)).all()
        products_by_id = {p.id: p for p in products}

        # Verify all products exist
        for pid in product_ids:
            if pid not in products_by_id:
                raise OrderValidationError(f"Product with ID {pid} was not found in the catalog.")

        # Verify sufficient stock
        for pid, requested_qty in item_quantities.items():
            product = products_by_id[pid]
            if product.stock_quantity < requested_qty:
                raise InsufficientStockError(
                    f"Insufficient stock for '{product.name}'. Available: {product.stock_quantity}, requested: {requested_qty}."
                )

        # 4. Server-side price calculation (never trusting client prices)
        order_items_to_create = []
        subtotal = 0.0

        for pid, requested_qty in item_quantities.items():
            product = products_by_id[pid]
            unit_price = round(float(product.price), 2)
            line_total = round(unit_price * requested_qty, 2)
            subtotal = round(subtotal + line_total, 2)

            order_item = OrderItem(
                product_id=product.id,
                product_name=product.name,  # Purchase-time snapshot
                unit_price=unit_price,      # Purchase-time snapshot
                quantity=requested_qty,
                line_total=line_total,
            )
            order_items_to_create.append(order_item)

        # Apply delivery rules: free if subtotal >= 100, otherwise $5.00
        delivery_fee = 0.0 if subtotal >= 100.0 else 5.0
        total_amount = round(subtotal + delivery_fee, 2)

        # 5. Create Order object
        order_reference = cls.generate_unique_order_reference()
        order = Order(
            order_reference=order_reference,
            customer_name=str(payload["customer_name"]).strip(),
            customer_email=str(payload["customer_email"]).strip(),
            customer_phone=re.sub(r"[\s\-]", "", str(payload["customer_phone"]).strip()),
            delivery_address=str(payload["delivery_address"]).strip(),
            city=str(payload["city"]).strip(),
            postal_code=str(payload["postal_code"]).strip(),
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total_amount=total_amount,
            status="CONFIRMED",
        )

        # 6. Execute atomic transaction: insert order, insert items, reduce stock
        try:
            db.session.add(order)
            db.session.flush()  # Generates order.id for foreign key

            for item in order_items_to_create:
                item.order_id = order.id
                # Deduct inventory stock
                product = products_by_id[item.product_id]
                product.stock_quantity -= item.quantity
                db.session.add(item)

            db.session.commit()
            return order
        except Exception as exc:
            db.session.rollback()
            raise exc

    @classmethod
    def get_order_by_reference(cls, reference: str) -> Optional[Order]:
        """Retrieve order and items by reference code."""
        if not reference or not reference.strip():
            return None
        return Order.query.filter_by(order_reference=reference.strip().upper()).first()
