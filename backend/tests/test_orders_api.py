import pytest
from app.database import seed_db
from app.models.db import db
from app.models.product import Product
from app.models.order import Order


@pytest.fixture(autouse=True)
def populate_sample_products(app):
    """Ensure sample products exist for each test."""
    with app.app_context():
        seed_db()


def get_valid_order_payload():
    return {
        "customer_name": "Rohan Sharma",
        "customer_email": "rohan.sharma@example.com",
        "customer_phone": "9876543210",
        "delivery_address": "Flat 402, Green Valley Apartments, MG Road",
        "city": "Bengaluru",
        "postal_code": "560001",
        "items": [
            {"product_id": 1, "quantity": 1},
            {"product_id": 2, "quantity": 2},
        ],
    }


def test_successful_order_creation(client, app):
    """Test creating an order successfully with valid items and customer info."""
    payload = get_valid_order_payload()
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 201

    data = response.get_json()
    assert "order" in data
    order = data["order"]
    assert order["order_reference"].startswith("ORD-")
    assert order["customer_name"] == "Rohan Sharma"
    assert order["customer_phone"] == "9876543210"
    assert order["status"] == "CONFIRMED"
    assert len(order["items"]) == 2

    # Check snapshots
    item1 = next(it for it in order["items"] if it["product_id"] == 1)
    assert item1["unit_price"] == 89.99
    assert item1["quantity"] == 1
    assert item1["line_total"] == 89.99

    item2 = next(it for it in order["items"] if it["product_id"] == 2)
    assert item2["unit_price"] == 49.50
    assert item2["quantity"] == 2
    assert item2["line_total"] == 99.00

    # Subtotal = 89.99 + 99.00 = 188.99 (>= 100 -> delivery fee 0)
    assert order["subtotal"] == 188.99
    assert order["delivery_fee"] == 0.0
    assert order["total_amount"] == 188.99


def test_invalid_customer_details(client):
    """Test validation errors for invalid customer fields."""
    base = get_valid_order_payload()

    # Empty name
    bad = {**base, "customer_name": ""}
    r = client.post("/api/orders", json=bad)
    assert r.status_code == 400
    assert "name" in r.get_json()["error"].lower()

    # Invalid email
    bad = {**base, "customer_email": "invalid-email"}
    r = client.post("/api/orders", json=bad)
    assert r.status_code == 400
    assert "email" in r.get_json()["error"].lower()

    # Invalid phone (less than 10 digits or invalid prefix)
    bad = {**base, "customer_phone": "12345"}
    r = client.post("/api/orders", json=bad)
    assert r.status_code == 400
    assert "mobile" in r.get_json()["error"].lower()

    # Invalid postal code (not 6 digits)
    bad = {**base, "postal_code": "123"}
    r = client.post("/api/orders", json=bad)
    assert r.status_code == 400
    assert "postal" in r.get_json()["error"].lower()


def test_missing_products_in_order(client):
    """Test ordering a non-existent product ID returns 400."""
    payload = get_valid_order_payload()
    payload["items"] = [{"product_id": 99999, "quantity": 1}]
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 400
    assert "not found" in response.get_json()["error"].lower()


def test_invalid_quantities(client):
    """Test ordering zero or negative quantity is rejected."""
    payload = get_valid_order_payload()

    # Quantity 0
    payload["items"] = [{"product_id": 1, "quantity": 0}]
    r = client.post("/api/orders", json=payload)
    assert r.status_code == 400

    # Negative quantity
    payload["items"] = [{"product_id": 1, "quantity": -5}]
    r = client.post("/api/orders", json=payload)
    assert r.status_code == 400

    # Non-integer quantity
    payload["items"] = [{"product_id": 1, "quantity": "two"}]
    r = client.post("/api/orders", json=payload)
    assert r.status_code == 400


def test_insufficient_stock_rejection(client, app):
    """Test ordering more than available stock is rejected."""
    with app.app_context():
        p = db.session.get(Product, 1)
        initial_stock = p.stock_quantity

    payload = get_valid_order_payload()
    payload["items"] = [{"product_id": 1, "quantity": initial_stock + 10}]
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 400
    assert "insufficient stock" in response.get_json()["error"].lower()

    # Verify stock remained untouched
    with app.app_context():
        p = db.session.get(Product, 1)
        assert p.stock_quantity == initial_stock


def test_server_side_price_calculation_ignores_client_tampering(client):
    """Test server recalculates real database price regardless of frontend tampering."""
    payload = get_valid_order_payload()
    payload["items"] = [
        {"product_id": 1, "quantity": 1, "price": 0.01, "subtotal": 0.01, "total": 0.01}
    ]
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 201

    order = response.get_json()["order"]
    assert order["items"][0]["unit_price"] == 89.99
    assert order["subtotal"] == 89.99
    # Subtotal < 100 -> $5.00 delivery fee
    assert order["delivery_fee"] == 5.0
    assert order["total_amount"] == 94.99


def test_delivery_fee_threshold(client):
    """Test delivery fee rules: free if subtotal >= 100, $5.00 otherwise."""
    # Under $100: Product 2 ($49.50) x 1 = $49.50
    p1 = get_valid_order_payload()
    p1["items"] = [{"product_id": 2, "quantity": 1}]
    r1 = client.post("/api/orders", json=p1)
    assert r1.status_code == 201
    assert r1.get_json()["order"]["delivery_fee"] == 5.0
    assert r1.get_json()["order"]["total_amount"] == 54.50

    # Over $100: Product 4 ($199.99) x 1 = $199.99
    p2 = get_valid_order_payload()
    p2["items"] = [{"product_id": 4, "quantity": 1}]
    r2 = client.post("/api/orders", json=p2)
    assert r2.status_code == 201
    assert r2.get_json()["order"]["delivery_fee"] == 0.0
    assert r2.get_json()["order"]["total_amount"] == 199.99


def test_stock_reduction_after_successful_order(client, app):
    """Test product inventory decreases accurately after an order succeeds."""
    with app.app_context():
        initial_stock = db.session.get(Product, 1).stock_quantity

    payload = get_valid_order_payload()
    payload["items"] = [{"product_id": 1, "quantity": 3}]
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 201

    with app.app_context():
        updated_stock = db.session.get(Product, 1).stock_quantity
        assert updated_stock == initial_stock - 3


def test_no_stock_reduction_after_failed_order(client, app):
    """Test inventory is not deducted if an order fails validation."""
    with app.app_context():
        initial_stock = db.session.get(Product, 1).stock_quantity

    payload = get_valid_order_payload()
    # 1 valid item and 1 non-existent item
    payload["items"] = [
        {"product_id": 1, "quantity": 2},
        {"product_id": 88888, "quantity": 1},
    ]
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 400

    # Stock of product 1 must be unchanged
    with app.app_context():
        assert db.session.get(Product, 1).stock_quantity == initial_stock


def test_order_retrieval_by_reference(client):
    """Test retrieving an order by its reference code."""
    payload = get_valid_order_payload()
    create_res = client.post("/api/orders", json=payload)
    assert create_res.status_code == 201
    ref = create_res.get_json()["order"]["order_reference"]

    get_res = client.get(f"/api/orders/{ref}")
    assert get_res.status_code == 200
    retrieved = get_res.get_json()["order"]
    assert retrieved["order_reference"] == ref
    assert retrieved["customer_name"] == "Rohan Sharma"
    assert len(retrieved["items"]) == 2


def test_order_retrieval_unknown_reference(client):
    """Test retrieving a non-existent reference returns 404."""
    response = client.get("/api/orders/ORD-99999999-XXXX")
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data


def test_transaction_rollback_when_db_error_occurs(client, monkeypatch, app):
    """Test atomic rollback when an unexpected error occurs during order transaction."""
    with app.app_context():
        initial_stock = db.session.get(Product, 1).stock_quantity

    payload = get_valid_order_payload()

    def mock_commit():
        raise Exception("Simulated database failure during checkout")

    from app.models.db import db as app_db
    monkeypatch.setattr(app_db.session, "commit", mock_commit)

    response = client.post("/api/orders", json=payload)
    assert response.status_code == 500

    # Stock must remain unchanged after rollback
    with app.app_context():
        assert db.session.get(Product, 1).stock_quantity == initial_stock
        assert Order.query.count() == 0
