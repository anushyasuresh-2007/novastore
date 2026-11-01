import logging
from flask import Blueprint, request, jsonify
from app.services.order_service import (
    OrderService,
    OrderValidationError,
    InsufficientStockError,
)

logger = logging.getLogger(__name__)

order_bp = Blueprint("orders", __name__, url_prefix="/api")


@order_bp.route("/orders", methods=["POST"])
def create_order():
    """
    Create a new order, verifying stock and recalculating prices on the server.
    Expected JSON payload:
    {
      "customer_name": "...",
      "customer_email": "...",
      "customer_phone": "...",
      "delivery_address": "...",
      "city": "...",
      "postal_code": "...",
      "items": [
        {"product_id": 1, "quantity": 2}
      ]
    }
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()

    try:
        order = OrderService.create_order(data)
        return jsonify({
            "message": "Order placed successfully",
            "order": order.to_dict(include_items=True),
        }), 201
    except OrderValidationError as err:
        return jsonify({"error": str(err)}), 400
    except InsufficientStockError as err:
        return jsonify({"error": str(err)}), 400
    except Exception as exc:
        logger.exception("Unexpected error creating order")
        return jsonify({"error": "Failed to process order due to an unexpected server error."}), 500


@order_bp.route("/orders/<string:reference>", methods=["GET"])
def get_order_by_reference(reference: str):
    """Retrieve full details of an order by its unique reference code."""
    clean_ref = reference.strip().upper()
    order = OrderService.get_order_by_reference(clean_ref)

    if order is None:
        return jsonify({"error": f"Order reference '{clean_ref}' was not found."}), 404

    return jsonify({
        "order": order.to_dict(include_items=True)
    }), 200
