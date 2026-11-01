"""AdminService handling dashboard analytics, administrative product CRUD, and order management."""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import func
from app.models.db import db
from app.models.product import Product
from app.models.order import Order
from app.models.order_item import OrderItem

VALID_ORDER_STATUSES = ["PENDING", "CONFIRMED", "SHIPPED", "DELIVERED", "CANCELLED"]

# State machine defining valid order lifecycle transitions
ALLOWED_ORDER_STATUS_TRANSITIONS: Dict[str, set] = {
    "PENDING": {"PENDING", "CONFIRMED", "CANCELLED"},
    "CONFIRMED": {"CONFIRMED", "SHIPPED", "CANCELLED"},
    "SHIPPED": {"SHIPPED", "DELIVERED", "CANCELLED"},
    "DELIVERED": {"DELIVERED"},   # Final terminal state
    "CANCELLED": {"CANCELLED"},   # Final terminal state
}



class AdminService:
    """Service encapsulating administrator operations and dashboard metrics."""

    @classmethod
    def get_dashboard_stats(cls) -> Dict[str, Any]:
        """Aggregate high-level KPIs and metrics for the dashboard."""
        total_products = Product.query.count()
        active_products = Product.query.filter_by(is_active=True).count()

        total_orders = Order.query.count()

        # Total warehouse stock quantity across all products
        inventory_sum = db.session.query(func.coalesce(func.sum(Product.stock_quantity), 0)).scalar()

        # Segregate sales by currency to never combine USD and INR amounts into one misleading total
        sales_inr = db.session.query(
            func.coalesce(func.sum(Order.total_amount), 0.0)
        ).filter(Order.status != "CANCELLED", Order.currency == "INR").scalar()

        sales_usd = db.session.query(
            func.coalesce(func.sum(Order.total_amount), 0.0)
        ).filter(Order.status != "CANCELLED", Order.currency == "USD").scalar()

        # Orders by status breakdown
        status_counts = (
            db.session.query(Order.status, func.count(Order.id))
            .group_by(Order.status)
            .all()
        )
        status_map = {status: 0 for status in VALID_ORDER_STATUSES}
        for st, count in status_counts:
            status_map[st] = count

        # Low stock products (stock <= 5)
        low_stock_products = (
            Product.query.filter(Product.stock_quantity <= 5, Product.is_active == True)
            .order_by(Product.stock_quantity.asc())
            .limit(5)
            .all()
        )

        # Recent 5 orders
        recent_orders = (
            Order.query.order_by(Order.created_at.desc())
            .limit(5)
            .all()
        )

        return {
            "total_products": total_products,
            "active_products": active_products,
            "total_orders": total_orders,
            "total_inventory": int(inventory_sum or 0),
            "total_sales": round(float(sales_inr or 0.0), 2),  # Active store currency (INR)
            "total_sales_inr": round(float(sales_inr or 0.0), 2),
            "total_sales_usd": round(float(sales_usd or 0.0), 2),
            "currency": "INR",
            "orders_by_status": status_map,
            "low_stock_count": len(low_stock_products),
            "low_stock_products": [p.to_dict() for p in low_stock_products],
            "recent_orders": [o.to_dict(include_items=False) for o in recent_orders],
        }

    @classmethod
    def list_products(
        cls,
        search: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Product]:
        """Retrieve all products for administrative viewing with optional filters."""
        query = Product.query

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(Product.name.ilike(term))

        if category and category.strip() and category.strip().lower() != "all":
            query = query.filter(func.lower(Product.category) == category.strip().lower())

        if status:
            clean_status = status.strip().lower()
            if clean_status == "active":
                query = query.filter(Product.is_active == True)
            elif clean_status == "inactive":
                query = query.filter(Product.is_active == False)
            elif clean_status == "out_of_stock":
                query = query.filter(Product.stock_quantity == 0)
            elif clean_status == "low_stock":
                query = query.filter(Product.stock_quantity <= 5, Product.stock_quantity > 0)

        return query.order_by(Product.id.asc()).all()

    @classmethod
    def get_product(cls, product_id: int) -> Optional[Product]:
        """Fetch a product by ID, including inactive products."""
        return db.session.get(Product, product_id)

    @classmethod
    def create_product(cls, data: Dict[str, Any]) -> Product:
        """Validate and create a new product."""
        name = str(data.get("name", "")).strip()
        description = str(data.get("description", "")).strip()
        category = str(data.get("category", "")).strip()
        image_path = str(data.get("image_path", "")).strip()

        if not name or len(name) < 2:
            raise ValueError("Product name must be at least 2 characters long.")
        if not description or len(description) < 5:
            raise ValueError("Product description must be at least 5 characters long.")
        if not category:
            raise ValueError("Product category is required.")

        try:
            price = round(float(data.get("price")), 2)
            if price < 0:
                raise ValueError("Price cannot be negative.")
        except (TypeError, ValueError) as err:
            raise ValueError(f"Invalid price value: {err}")

        try:
            stock = int(data.get("stock_quantity", 0))
            if stock < 0:
                raise ValueError("Stock quantity cannot be negative.")
        except (TypeError, ValueError) as err:
            raise ValueError(f"Invalid stock quantity: {err}")

        product = Product(
            name=name,
            description=description,
            category=category,
            price=price,
            currency=str(data.get("currency", "INR")).strip().upper() or "INR",
            stock_quantity=stock,
            image_path=image_path or "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80",
            is_active=bool(data.get("is_active", True)),
        )

        db.session.add(product)
        db.session.commit()
        return product

    @classmethod
    def update_product(cls, product_id: int, data: Dict[str, Any]) -> Product:
        """Validate and update an existing product record."""
        product = db.session.get(Product, product_id)
        if not product:
            raise LookupError(f"Product #{product_id} not found.")

        if "name" in data:
            name = str(data["name"]).strip()
            if not name or len(name) < 2:
                raise ValueError("Product name must be at least 2 characters long.")
            product.name = name

        if "description" in data:
            desc = str(data["description"]).strip()
            if not desc or len(desc) < 5:
                raise ValueError("Product description must be at least 5 characters long.")
            product.description = desc

        if "category" in data:
            cat = str(data["category"]).strip()
            if not cat:
                raise ValueError("Category cannot be empty.")
            product.category = cat

        if "price" in data:
            try:
                price = round(float(data["price"]), 2)
                if price < 0:
                    raise ValueError("Price cannot be negative.")
                product.price = price
            except (TypeError, ValueError) as err:
                raise ValueError(f"Invalid price value: {err}")

        if "stock_quantity" in data:
            try:
                stock = int(data["stock_quantity"])
                if stock < 0:
                    raise ValueError("Stock quantity cannot be negative.")
                product.stock_quantity = stock
            except (TypeError, ValueError) as err:
                raise ValueError(f"Invalid stock quantity: {err}")

        if "image_path" in data:
            product.image_path = str(data["image_path"]).strip()

        if "is_active" in data:
            product.is_active = bool(data["is_active"])

        product.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return product

    @classmethod
    def delete_product(cls, product_id: int) -> Dict[str, Any]:
        """
        Safely delete or archive a product.
        If the product has historical orders, it is soft-deleted (is_active=False)
        to protect relational integrity and preserve customer order records.
        If the product has no order history, it is permanently removed.
        """
        product = db.session.get(Product, product_id)
        if not product:
            raise LookupError(f"Product #{product_id} not found.")

        # Check if product is referenced in order items
        order_count = OrderItem.query.filter_by(product_id=product.id).count()

        if order_count > 0:
            # Soft delete to preserve order items and snapshots
            product.is_active = False
            product.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            return {
                "action": "archived",
                "message": f"Product #{product_id} is referenced in {order_count} historical order(s). It has been safely deactivated from the storefront without deleting order records.",
                "product": product.to_dict(),
            }
        else:
            # Safe to hard delete as no foreign key constraints are violated
            db.session.delete(product)
            db.session.commit()
            return {
                "action": "deleted",
                "message": f"Product #{product_id} ('{product.name}') has been permanently removed.",
            }

    @classmethod
    def list_orders(
        cls,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Order]:
        """Retrieve orders with optional status and customer search."""
        query = Order.query

        if status and status.strip() and status.strip().upper() != "ALL":
            query = query.filter(Order.status == status.strip().upper())

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                (Order.order_reference.ilike(term))
                | (Order.customer_name.ilike(term))
                | (Order.customer_email.ilike(term))
                | (Order.customer_phone.ilike(term))
            )

        return query.order_by(Order.created_at.desc()).all()

    @classmethod
    def get_order(cls, id_or_ref: str | int) -> Optional[Order]:
        """Fetch order details by numeric primary key ID or UUID order reference."""
        if isinstance(id_or_ref, int) or (isinstance(id_or_ref, str) and id_or_ref.isdigit()):
            return db.session.get(Order, int(id_or_ref))
        else:
            clean_ref = str(id_or_ref).strip().upper()
            return Order.query.filter_by(order_reference=clean_ref).first()

    @classmethod
    def update_order_status(cls, id_or_ref: str | int, new_status: str) -> Order:
        """Update an order's fulfillment status with controlled status transition validation."""
        order = cls.get_order(id_or_ref)
        if not order:
            raise LookupError(f"Order '{id_or_ref}' not found.")

        clean_status = str(new_status).strip().upper()
        if clean_status not in VALID_ORDER_STATUSES:
            raise ValueError(
                f"Invalid order status '{new_status}'. Allowed values: {', '.join(VALID_ORDER_STATUSES)}"
            )

        current_status = order.status.upper() if order.status else "PENDING"
        allowed_transitions = ALLOWED_ORDER_STATUS_TRANSITIONS.get(current_status, {current_status})
        if clean_status not in allowed_transitions:
            raise ValueError(
                f"Cannot transition order from '{current_status}' to '{clean_status}'. "
                f"Allowed transitions from '{current_status}': {', '.join(sorted(allowed_transitions))}"
            )

        order.status = clean_status
        order.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return order
