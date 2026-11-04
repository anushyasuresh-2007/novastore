"""API routes package."""
from app.routes.product_routes import product_bp
from app.routes.order_routes import order_bp
from app.routes.admin_routes import admin_bp

__all__ = ["product_bp", "order_bp", "admin_bp"]
