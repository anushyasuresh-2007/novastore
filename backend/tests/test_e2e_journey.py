import pytest
from app.database import seed_db
from app.models.db import db
from app.models.product import Product


@pytest.fixture(autouse=True)
def setup_db(app):
    with app.app_context():
        seed_db()


def test_complete_e2e_customer_journey(client, app):
    """
    Test the full 11-step customer shopping journey:
    1. Open storefront (categories and initial product catalog).
    2. Search for a product.
    3. Filter and sort products.
    4. Open product details modal.
    5. Add products to the cart.
    6. Change quantities and verify line/subtotal calculations.
    7. Proceed to checkout.
    8. Enter customer details.
    9. Place order via simulated checkout.
    10. Retrieve order confirmation and reference.
    11. Verify product inventory was decremented in database.
    """
    # Step 1: Open storefront
    cat_res = client.get("/api/categories")
    assert cat_res.status_code == 200
    categories = cat_res.get_json()["categories"]
    assert len(categories) >= 3

    catalog_res = client.get("/api/products")
    assert catalog_res.status_code == 200
    all_products = catalog_res.get_json()["products"]
    assert len(all_products) >= 10

    # Step 2: Search for a product
    search_res = client.get("/api/products?search=Keyboard")
    assert search_res.status_code == 200
    search_matches = search_res.get_json()["products"]
    assert len(search_matches) >= 1
    assert any("Keyboard" in p["name"] for p in search_matches)

    # Step 3: Filter by category and sort by price ascending
    filtered_res = client.get("/api/products?category=Electronics&sort=price_asc")
    assert filtered_res.status_code == 200
    filtered_products = filtered_res.get_json()["products"]
    assert len(filtered_products) >= 2
    prices = [p["price"] for p in filtered_products]
    assert prices == sorted(prices)

    # Step 4: Open product details for item #1
    p1_details_res = client.get("/api/products/1")
    assert p1_details_res.status_code == 200
    p1 = p1_details_res.get_json()
    assert p1["id"] == 1
    initial_stock_p1 = p1["stock_quantity"]

    # Step 5 & 6: Add to cart & simulate cart line calculations
    # Select Product 1 (qty 2) and Product 2 (qty 1)
    p2_details_res = client.get("/api/products/2")
    p2 = p2_details_res.get_json()
    initial_stock_p2 = p2["stock_quantity"]

    cart = [
        {"product_id": p1["id"], "unit_price": p1["price"], "quantity": 2},
        {"product_id": p2["id"], "unit_price": p2["price"], "quantity": 1},
    ]

    expected_subtotal = round(p1["price"] * 2 + p2["price"] * 1, 2)
    expected_delivery = 0.0 if expected_subtotal >= 100.0 else 5.0
    expected_total = round(expected_subtotal + expected_delivery, 2)

    # Step 7 & 8: Checkout customer payload
    checkout_payload = {
        "customer_name": "Ananya Sen",
        "customer_email": "ananya.sen@example.com",
        "customer_phone": "9876501234",
        "delivery_address": "Flat 502, Tower B, Prestige Palms",
        "city": "Kolkata",
        "postal_code": "700001",
        "items": [
            {"product_id": item["product_id"], "quantity": item["quantity"]}
            for item in cart
        ],
    }

    # Step 9: Place order
    order_res = client.post("/api/orders", json=checkout_payload)
    assert order_res.status_code == 201
    created_order = order_res.get_json()["order"]

    order_ref = created_order["order_reference"]
    assert order_ref.startswith("ORD-")
    assert created_order["subtotal"] == expected_subtotal
    assert created_order["delivery_fee"] == expected_delivery
    assert created_order["total_amount"] == expected_total
    assert created_order["status"] == "CONFIRMED"
    assert len(created_order["items"]) == 2

    # Step 10: Retrieve order confirmation by reference
    retrieval_res = client.get(f"/api/orders/{order_ref}")
    assert retrieval_res.status_code == 200
    confirmed = retrieval_res.get_json()["order"]
    assert confirmed["order_reference"] == order_ref
    assert confirmed["customer_name"] == "Ananya Sen"
    assert confirmed["city"] == "Kolkata"

    # Step 11: Verify inventory changes in the database
    with app.app_context():
        p1_db = db.session.get(Product, 1)
        p2_db = db.session.get(Product, 2)
        assert p1_db.stock_quantity == initial_stock_p1 - 2
        assert p2_db.stock_quantity == initial_stock_p2 - 1
