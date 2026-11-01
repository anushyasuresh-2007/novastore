from flask import Blueprint, request, jsonify
from app.services.product_service import ProductService

product_bp = Blueprint("products", __name__, url_prefix="/api")


@product_bp.route("/products", methods=["GET"])
def list_products():
    """
    List products with optional search, category filtering, price range, and sorting.
    Query parameters:
      - search: string
      - category: string
      - min_price: float >= 0
      - max_price: float >= 0
      - sort: price_asc | price_desc | name_asc | name_desc | newest
    """
    search = request.args.get("search", request.args.get("q", type=str))
    category = request.args.get("category", type=str)
    sort_by = request.args.get("sort", request.args.get("sort_by", type=str))

    # Parse and validate min_price
    min_price_raw = request.args.get("min_price")
    min_price = None
    if min_price_raw is not None and min_price_raw.strip() != "":
        try:
            min_price = float(min_price_raw)
            if min_price < 0:
                return jsonify({"error": "min_price must be a non-negative number"}), 400
        except ValueError:
            return jsonify({"error": "min_price must be a valid numeric value"}), 400

    # Parse and validate max_price
    max_price_raw = request.args.get("max_price")
    max_price = None
    if max_price_raw is not None and max_price_raw.strip() != "":
        try:
            max_price = float(max_price_raw)
            if max_price < 0:
                return jsonify({"error": "max_price must be a non-negative number"}), 400
        except ValueError:
            return jsonify({"error": "max_price must be a valid numeric value"}), 400

    # Validate price range relation
    if min_price is not None and max_price is not None and min_price > max_price:
        return jsonify({"error": "min_price cannot be greater than max_price"}), 400

    # Validate sort parameter if provided
    valid_sorts = set(ProductService.SORT_OPTIONS.keys())
    if sort_by and sort_by not in valid_sorts:
        return jsonify({
            "error": f"Invalid sort parameter '{sort_by}'. Allowed values: {', '.join(sorted(valid_sorts))}"
        }), 400

    products = ProductService.get_products(
        search=search,
        category=category,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
    )

    return jsonify({
        "products": [p.to_dict() for p in products],
        "count": len(products),
        "filters": {
            "search": search.strip() if search else None,
            "category": category.strip() if category else None,
            "min_price": min_price,
            "max_price": max_price,
            "sort": sort_by,
        }
    }), 200


@product_bp.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id: int):
    """Retrieve full details of a specific product by ID."""
    product = ProductService.get_product_by_id(product_id)
    if product is None:
        return jsonify({"error": f"Product with ID {product_id} not found"}), 404

    return jsonify(product.to_dict()), 200


@product_bp.route("/categories", methods=["GET"])
def get_categories():
    """Retrieve all available product categories with item counts."""
    categories = ProductService.get_categories()
    return jsonify({"categories": categories}), 200
