"""Admin routes blueprint handling administrator authentication, dashboard, products CRUD, and orders."""
from flask import Blueprint, request, jsonify
from app.services.auth_service import AuthService, admin_required
from app.services.admin_service import AdminService, VALID_ORDER_STATUSES

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# ============================================================================
# Authentication Endpoints
# ============================================================================

@admin_bp.route("/login", methods=["POST"])
def admin_login():
    """
    Authenticate administrator credentials and return signed authorization bearer token.
    Accepts JSON: { "username": "..." (or "email"), "password": "..." }
    """
    data = request.get_json(silent=True) or {}
    identifier = data.get("username") or data.get("email") or ""
    password = data.get("password") or ""

    if not identifier.strip() or not password:
        return jsonify({"error": "Username/email and password are required."}), 400

    admin = AuthService.authenticate(identifier, password)
    if not admin:
        return jsonify({"error": "Invalid administrator credentials."}), 401

    token = AuthService.generate_token(admin)
    return jsonify({
        "message": "Authentication successful.",
        "token": token,
        "admin": admin.to_dict(),
    }), 200


@admin_bp.route("/logout", methods=["POST"])
@admin_required
def admin_logout():
    """Log out the current administrator session."""
    return jsonify({"message": "Administrator logged out successfully."}), 200


@admin_bp.route("/me", methods=["GET"])
@admin_required
def admin_me():
    """Verify administrator session and retrieve authenticated profile."""
    return jsonify({"admin": request.current_admin.to_dict()}), 200


# ============================================================================
# Dashboard Analytics Endpoints
# ============================================================================

@admin_bp.route("/stats", methods=["GET"])
@admin_required
def get_stats():
    """Retrieve high-level dashboard metrics, sales, inventory, and recent orders."""
    stats = AdminService.get_dashboard_stats()
    return jsonify(stats), 200


# ============================================================================
# Product Management Endpoints
# ============================================================================

@admin_bp.route("/products", methods=["GET"])
@admin_required
def list_products():
    """Retrieve all products for administrative view with optional search and category filters."""
    search = request.args.get("search")
    category = request.args.get("category")
    status = request.args.get("status")

    products = AdminService.list_products(search=search, category=category, status=status)
    return jsonify({
        "products": [p.to_dict() for p in products],
        "count": len(products),
    }), 200


@admin_bp.route("/products", methods=["POST"])
@admin_required
def create_product():
    """Create a new product in the catalog."""
    data = request.get_json(silent=True) or {}
    try:
        product = AdminService.create_product(data)
        return jsonify({
            "message": "Product created successfully.",
            "product": product.to_dict(),
        }), 201
    except ValueError as val_err:
        return jsonify({"error": str(val_err)}), 400
    except Exception as exc:
        return jsonify({"error": f"Failed to create product: {exc}"}), 500


@admin_bp.route("/products/<int:product_id>", methods=["GET"])
@admin_required
def get_product(product_id: int):
    """Retrieve a single product's details for administration."""
    product = AdminService.get_product(product_id)
    if not product:
        return jsonify({"error": f"Product #{product_id} not found."}), 404

    return jsonify({"product": product.to_dict()}), 200


@admin_bp.route("/products/<int:product_id>", methods=["PUT"])
@admin_required
def update_product(product_id: int):
    """Update details, price, or inventory of an existing product."""
    data = request.get_json(silent=True) or {}
    try:
        product = AdminService.update_product(product_id, data)
        return jsonify({
            "message": "Product updated successfully.",
            "product": product.to_dict(),
        }), 200
    except LookupError as lookup_err:
        return jsonify({"error": str(lookup_err)}), 404
    except ValueError as val_err:
        return jsonify({"error": str(val_err)}), 400
    except Exception as exc:
        return jsonify({"error": f"Failed to update product: {exc}"}), 500


@admin_bp.route("/products/<int:product_id>", methods=["DELETE"])
@admin_required
def delete_product(product_id: int):
    """Safely delete or archive a product without breaking order history."""
    try:
        result = AdminService.delete_product(product_id)
        return jsonify(result), 200
    except LookupError as lookup_err:
        return jsonify({"error": str(lookup_err)}), 404
    except Exception as exc:
        return jsonify({"error": f"Failed to delete product: {exc}"}), 500


# ============================================================================
# Order Management Endpoints
# ============================================================================

@admin_bp.route("/orders", methods=["GET"])
@admin_required
def list_orders():
    """Retrieve orders with optional status filter and customer search."""
    status = request.args.get("status")
    search = request.args.get("search")

    orders = AdminService.list_orders(status=status, search=search)
    return jsonify({
        "orders": [o.to_dict(include_items=True) for o in orders],
        "count": len(orders),
    }), 200


@admin_bp.route("/orders/<id_or_ref>", methods=["GET"])
@admin_required
def get_order(id_or_ref: str):
    """Retrieve full order details including purchased items snapshot and customer details."""
    order = AdminService.get_order(id_or_ref)
    if not order:
        return jsonify({"error": f"Order '{id_or_ref}' not found."}), 404

    return jsonify({"order": order.to_dict(include_items=True)}), 200


@admin_bp.route("/orders/<id_or_ref>/status", methods=["PATCH", "PUT"])
@admin_required
def update_order_status(id_or_ref: str):
    """Update order fulfillment status (PENDING, CONFIRMED, SHIPPED, DELIVERED, CANCELLED)."""
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")

    if not new_status:
        return jsonify({
            "error": f"Missing 'status'. Allowed values: {', '.join(VALID_ORDER_STATUSES)}"
        }), 400

    try:
        order = AdminService.update_order_status(id_or_ref, new_status)
        return jsonify({
            "message": f"Order status updated to '{order.status}'.",
            "order": order.to_dict(include_items=True),
        }), 200
    except LookupError as lookup_err:
        return jsonify({"error": str(lookup_err)}), 404
    except ValueError as val_err:
        return jsonify({"error": str(val_err)}), 400
    except Exception as exc:
        return jsonify({"error": f"Failed to update order status: {exc}"}), 500
