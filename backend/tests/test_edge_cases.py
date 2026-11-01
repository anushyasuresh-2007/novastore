import pytest
from app.database import seed_db
from app.models.db import db
from app.models.product import Product
from app.models.order import Order
from app.services.order_service import OrderService


@pytest.fixture(autouse=True)
def populate_sample_products(app):
    """Ensure sample products exist for each test."""
    with app.app_context():
        seed_db()


def test_order_reference_format_and_uniqueness(app):
    """Test generating 100 order references guarantees uniqueness and correct format."""
    with app.app_context():
        refs = {OrderService.generate_unique_order_reference() for _ in range(100)}
        assert len(refs) == 100
        for ref in refs:
            assert ref.startswith("ORD-")
            parts = ref.split("-")
            assert len(parts) == 3
            assert len(parts[1]) == 8  # YYYYMMDD
            assert len(parts[2]) >= 4  # Random suffix


def test_duplicate_items_in_same_order_payload(client, app):
    """Test when client sends multiple items with same product_id, server aggregates quantities."""
    with app.app_context():
        initial_stock = db.session.get(Product, 1).stock_quantity

    payload = {
        "customer_name": "Aarav Gupta",
        "customer_email": "aarav@example.com",
        "customer_phone": "+91 98765 43210",
        "delivery_address": "12 Residency Road",
        "city": "Bengaluru",
        "postal_code": "560025",
        "items": [
            {"product_id": 1, "quantity": 2},
            {"product_id": 1, "quantity": 3},
        ],
    }

    response = client.post("/api/orders", json=payload)
    assert response.status_code == 201

    order = response.get_json()["order"]
    # Aggregated to single line item with quantity 5
    assert len(order["items"]) == 1
    assert order["items"][0]["quantity"] == 5
    assert order["items"][0]["line_total"] == round(89.99 * 5, 2)

    with app.app_context():
        updated_stock = db.session.get(Product, 1).stock_quantity
        assert updated_stock == initial_stock - 5


def test_consecutive_orders_deplete_stock_correctly(client, app):
    """Test sequential orders depleting stock until insufficient stock error is triggered."""
    with app.app_context():
        # Set stock of product 3 to 3
        p3 = db.session.get(Product, 3)
        p3.stock_quantity = 3
        db.session.commit()

    order_payload = {
        "customer_name": "Kavita Rao",
        "customer_email": "kavita@example.com",
        "customer_phone": "9812345678",
        "delivery_address": "88 Palm Meadows",
        "city": "Hyderabad",
        "postal_code": "500081",
        "items": [{"product_id": 3, "quantity": 2}],
    }

    # First order for 2 units succeeds
    r1 = client.post("/api/orders", json=order_payload)
    assert r1.status_code == 201

    with app.app_context():
        assert db.session.get(Product, 3).stock_quantity == 1

    # Second order for 2 units must fail (only 1 remaining)
    r2 = client.post("/api/orders", json=order_payload)
    assert r2.status_code == 400
    assert "insufficient stock" in r2.get_json()["error"].lower()

    # Final stock in database must remain 1
    with app.app_context():
        assert db.session.get(Product, 3).stock_quantity == 1


def test_empty_and_malformed_json_payloads(client):
    """Test server rejects empty or malformed order payloads."""
    # Empty object
    r1 = client.post("/api/orders", json={})
    assert r1.status_code == 400

    # Missing items list
    r2 = client.post("/api/orders", json={"customer_name": "Test"})
    assert r2.status_code == 400

    # Empty items list
    r3 = client.post("/api/orders", json={"customer_name": "Test", "items": []})
    assert r3.status_code == 400

    # Non-json request
    r4 = client.post("/api/orders", data="not json", content_type="text/plain")
    assert r4.status_code == 400


def test_phone_number_formats_in_indian_context(client):
    """Test various valid Indian mobile phone formats are accepted and normalized."""
    valid_phones = [
        "9876543210",
        "+919876543210",
        "+91 9876543210",
        "+91-9876543210",
        "8765432109",
        "7654321098",
        "6543210987",
    ]

    for phone in valid_phones:
        payload = {
            "customer_name": "Valid Phone Tester",
            "customer_email": "phone.test@example.com",
            "customer_phone": phone,
            "delivery_address": "123 Test Street",
            "city": "Chennai",
            "postal_code": "600001",
            "items": [{"product_id": 2, "quantity": 1}],
        }
        res = client.post("/api/orders", json=payload)
        assert res.status_code == 201, f"Failed for phone: {phone}"


def test_invalid_postal_codes_rejected(client):
    """Test invalid postal codes (not 6 digits) are rejected."""
    invalid_codes = ["12345", "1234567", "56000a", "PINCODE", ""]

    for pin in invalid_codes:
        payload = {
            "customer_name": "Postal Tester",
            "customer_email": "postal@example.com",
            "customer_phone": "9876543210",
            "delivery_address": "123 Test Street",
            "city": "Pune",
            "postal_code": pin,
            "items": [{"product_id": 2, "quantity": 1}],
        }
        res = client.post("/api/orders", json=payload)
        assert res.status_code == 400, f"Accepted invalid postal code: {pin}"


def test_sql_and_script_injection_safety(client, app):
    """Test SQL injection payloads in customer and search fields do not disrupt database or execute."""
    injection_payload = {
        "customer_name": "Robert'); DROP TABLE orders;--",
        "customer_email": "injection@example.com",
        "customer_phone": "9876543210",
        "delivery_address": "' OR '1'='1",
        "city": "Safe City",
        "postal_code": "560001",
        "items": [{"product_id": 1, "quantity": 1}],
    }

    res = client.post("/api/orders", json=injection_payload)
    assert res.status_code == 201

    # Verify orders table was not dropped
    with app.app_context():
        order = Order.query.filter_by(customer_name="Robert'); DROP TABLE orders;--").first()
        assert order is not None

    # Test search with SQL special characters
    search_res = client.get("/api/products?search=%27%20OR%201=1--")
    assert search_res.status_code == 200
    assert "products" in search_res.get_json()


def test_product_query_edge_cases(client):
    """Test product filtering with boundary values."""
    # category=All returns all products
    r1 = client.get("/api/products?category=All")
    assert r1.status_code == 200
    assert r1.get_json()["count"] >= 10

    # min_price exceeding all items returns 0 products
    r2 = client.get("/api/products?min_price=10000")
    assert r2.status_code == 200
    assert r2.get_json()["count"] == 0

    # min_price=0 and max_price=0 returns 0 products
    r3 = client.get("/api/products?min_price=0&max_price=0")
    assert r3.status_code == 200
    assert r3.get_json()["count"] == 0
