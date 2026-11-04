import pytest
from app.models.db import db
from app.models.admin import Admin
from app.models.product import Product
from app.models.order import Order
from app.models.order_item import OrderItem
from app.services.auth_service import AuthService
from app.database import seed_db


@pytest.fixture
def admin_user(app):
    """Create a test administrator."""
    with app.app_context():
        admin = Admin(username="superadmin", email="superadmin@novastore.com")
        admin.set_password("AdminSecurePass123!")
        db.session.add(admin)
        db.session.commit()
        return admin.id


@pytest.fixture
def admin_token(app, admin_user):
    """Generate an authorization bearer token for the test administrator."""
    with app.app_context():
        admin = db.session.get(Admin, admin_user)
        return AuthService.generate_token(admin)



@pytest.fixture
def admin_headers(admin_token):
    """Provide standard authorization headers for admin requests."""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json",
    }


@pytest.fixture(autouse=True)
def seed_catalog(app):
    """Seed catalog products for tests."""
    with app.app_context():
        seed_db()


# ============================================================================
# Authentication Tests
# ============================================================================

def test_admin_login_success_with_username(client, admin_user):
    """Test successful administrator login sets secure HttpOnly cookie and omits token from body."""
    response = client.post("/api/admin/login", json={
        "username": "superadmin",
        "password": "AdminSecurePass123!",
    })
    assert response.status_code == 200
    set_cookie = response.headers.get("Set-Cookie", "")
    assert "admin_session=" in set_cookie
    assert "HttpOnly" in set_cookie
    data = response.get_json()
    assert "token" not in data  # Token strictly omitted from JSON body
    assert "csrf_token" in data
    assert data["admin"]["username"] == "superadmin"
    assert data["admin"]["email"] == "superadmin@novastore.com"
    assert "password_hash" not in data["admin"]


def test_admin_login_success_with_email(client, admin_user):
    """Test successful administrator login using email sets session cookie."""
    response = client.post("/api/admin/login", json={
        "email": "superadmin@novastore.com",
        "password": "AdminSecurePass123!",
    })
    assert response.status_code == 200
    assert "admin_session=" in response.headers.get("Set-Cookie", "")
    data = response.get_json()
    assert "token" not in data
    assert "csrf_token" in data
    assert data["admin"]["username"] == "superadmin"


def test_admin_login_invalid_password(client, admin_user):
    """Test login rejected with wrong password."""
    response = client.post("/api/admin/login", json={
        "username": "superadmin",
        "password": "WrongPasswordXYZ",
    })
    assert response.status_code == 401
    assert "error" in response.get_json()


def test_admin_login_unknown_user(client):
    """Test login rejected for non-existent admin."""
    response = client.post("/api/admin/login", json={
        "username": "non_existent_admin",
        "password": "SomePassword123!",
    })
    assert response.status_code == 401


def test_admin_login_missing_fields(client):
    """Test validation when required login fields are omitted."""
    res1 = client.post("/api/admin/login", json={"username": ""})
    assert res1.status_code == 400

    res2 = client.post("/api/admin/login", json={"password": ""})
    assert res2.status_code == 400


def test_admin_logout(client, admin_headers):
    """Test administrator logout endpoint."""
    response = client.post("/api/admin/logout", headers=admin_headers)
    assert response.status_code == 200
    assert "message" in response.get_json()


def test_admin_me_endpoint(client, admin_headers):
    """Test GET /api/admin/me session verification."""
    response = client.get("/api/admin/me", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["admin"]["username"] == "superadmin"


# ============================================================================
# Authorization & Protection Tests
# ============================================================================

def test_unauthorized_access_without_token(client):
    """Test protected admin endpoints reject unauthenticated access."""
    endpoints = [
        ("GET", "/api/admin/stats"),
        ("GET", "/api/admin/products"),
        ("POST", "/api/admin/products"),
        ("GET", "/api/admin/orders"),
    ]
    for method, path in endpoints:
        if method == "GET":
            res = client.get(path)
        else:
            res = client.post(path, json={})
        assert res.status_code == 401
        assert "error" in res.get_json()


def test_unauthorized_access_with_tampered_token(client):
    """Test token tampering triggers 401 Unauthorized."""
    headers = {"Authorization": "Bearer bad.token.tampered.signature"}
    res = client.get("/api/admin/stats", headers=headers)
    assert res.status_code == 401


def test_inactive_admin_forbidden(app, client):
    """Test deactivated admin account is forbidden."""
    with app.app_context():
        inactive = Admin(username="disabled_admin", email="inactive@novastore.com", is_active=False)
        inactive.set_password("AdminSecurePass123!")
        db.session.add(inactive)
        db.session.commit()
        token = AuthService.generate_token(inactive)

    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/admin/stats", headers=headers)
    assert res.status_code in (401, 403)


# ============================================================================
# Dashboard Analytics Tests
# ============================================================================

def test_dashboard_stats_metrics(client, admin_headers, app):
    """Test GET /api/admin/stats aggregates inventory, products, orders, and sales."""
    # Place a test order first
    with app.app_context():
        order = Order(
            order_reference="ORD-TEST-DASH-01",
            customer_name="Test Customer",
            customer_email="test@example.com",
            customer_phone="9876543210",
            delivery_address="123 Test St",
            city="Mumbai",
            postal_code="400001",
            subtotal=100.0,
            delivery_fee=0.0,
            total_amount=100.0,
            status="CONFIRMED",
        )
        db.session.add(order)
        db.session.commit()

    response = client.get("/api/admin/stats", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["total_products"] >= 30
    assert data["total_orders"] >= 1
    assert data["total_inventory"] > 0
    assert data["total_sales"] >= 100.0
    assert "orders_by_status" in data
    assert "recent_orders" in data


# ============================================================================
# Product Management CRUD Tests
# ============================================================================

def test_admin_create_product_success(client, admin_headers):
    """Test admin creating a new product."""
    payload = {
        "name": "Noise-Isolating Studio Earphones",
        "description": "High resolution armature dynamic in-ear monitor earphones.",
        "category": "Audio",
        "price": 79.99,
        "stock_quantity": 25,
        "image_path": "https://images.unsplash.com/photo-1590658268037",
        "is_active": True,
    }
    response = client.post("/api/admin/products", headers=admin_headers, json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["product"]["name"] == payload["name"]
    assert data["product"]["price"] == 79.99
    assert data["product"]["currency"] == "INR"
    assert data["product"]["stock_quantity"] == 25


def test_admin_create_product_validation(client, admin_headers):
    """Test input validation when creating a product."""
    # Missing name
    r1 = client.post("/api/admin/products", headers=admin_headers, json={
        "name": "",
        "description": "Valid description text",
        "category": "Audio",
        "price": 10.0,
        "stock_quantity": 5,
    })
    assert r1.status_code == 400

    # Negative price
    r2 = client.post("/api/admin/products", headers=admin_headers, json={
        "name": "Test Item",
        "description": "Valid description text",
        "category": "Audio",
        "price": -5.0,
        "stock_quantity": 5,
    })
    assert r2.status_code == 400

    # Negative stock
    r3 = client.post("/api/admin/products", headers=admin_headers, json={
        "name": "Test Item",
        "description": "Valid description text",
        "category": "Audio",
        "price": 10.0,
        "stock_quantity": -1,
    })
    assert r3.status_code == 400


def test_admin_update_product(client, admin_headers):
    """Test updating existing product price and stock quantity."""
    response = client.put("/api/admin/products/1", headers=admin_headers, json={
        "price": 99.95,
        "stock_quantity": 42,
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["product"]["price"] == 99.95
    assert data["product"]["stock_quantity"] == 42


def test_admin_safe_delete_unreferenced_product(client, admin_headers):
    """Test hard-deleting a product that has no order history."""
    # First create a temporary product
    created = client.post("/api/admin/products", headers=admin_headers, json={
        "name": "Disposable Test Item",
        "description": "Product intended for deletion test.",
        "category": "Accessories",
        "price": 5.0,
        "stock_quantity": 10,
    }).get_json()["product"]

    # Delete it
    response = client.delete(f"/api/admin/products/{created['id']}", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["action"] == "deleted"

    # Confirm it no longer exists
    check = client.get(f"/api/admin/products/{created['id']}", headers=admin_headers)
    assert check.status_code == 404


def test_admin_safe_delete_ordered_product_archives_without_breaking_orders(client, admin_headers, app):
    """
    Test that deleting a product with historical orders soft-deletes (archives)
    it to preserve order history and relational integrity.
    """
    with app.app_context():
        # Place an order referencing Product 2
        order = Order(
            order_reference="ORD-HISTORICAL-REF-01",
            customer_name="History Preserved",
            customer_email="preserve@example.com",
            customer_phone="9811223344",
            delivery_address="456 Heritage Rd",
            city="Delhi",
            postal_code="110001",
            subtotal=49.50,
            delivery_fee=5.0,
            total_amount=54.50,
            status="CONFIRMED",
        )
        db.session.add(order)
        db.session.flush()

        item = OrderItem(
            order_id=order.id,
            product_id=2,
            product_name="Precision Ergonomic Optical Mouse",
            unit_price=49.50,
            quantity=1,
            line_total=49.50,
        )
        db.session.add(item)
        db.session.commit()

    # Admin attempts to delete Product 2
    response = client.delete("/api/admin/products/2", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["action"] == "archived"
    assert data["product"]["is_active"] is False

    # Verify order and item still exist and are completely intact
    with app.app_context():
        saved_order = Order.query.filter_by(order_reference="ORD-HISTORICAL-REF-01").first()
        assert saved_order is not None
        assert len(saved_order.items) == 1
        assert saved_order.items[0].product_name == "Precision Ergonomic Optical Mouse"


# ============================================================================
# Order Management Tests
# ============================================================================

def test_admin_orders_list_and_filter(client, admin_headers, app):
    """Test listing orders with status filter."""
    with app.app_context():
        o1 = Order(
            order_reference="ORD-FILTER-01",
            customer_name="Alice",
            customer_email="alice@example.com",
            customer_phone="9876543210",
            delivery_address="Road 1",
            city="Chennai",
            postal_code="600001",
            subtotal=50.0,
            delivery_fee=5.0,
            total_amount=55.0,
            status="PENDING",
        )
        o2 = Order(
            order_reference="ORD-FILTER-02",
            customer_name="Bob",
            customer_email="bob@example.com",
            customer_phone="9876543210",
            delivery_address="Road 2",
            city="Pune",
            postal_code="411001",
            subtotal=150.0,
            delivery_fee=0.0,
            total_amount=150.0,
            status="SHIPPED",
        )
        db.session.add_all([o1, o2])
        db.session.commit()

    # Filter status=PENDING
    res_pending = client.get("/api/admin/orders?status=PENDING", headers=admin_headers)
    assert res_pending.status_code == 200
    pending_orders = res_pending.get_json()["orders"]
    assert any(o["order_reference"] == "ORD-FILTER-01" for o in pending_orders)
    assert all(o["status"] == "PENDING" for o in pending_orders)


def test_admin_get_order_details(client, admin_headers, app):
    """Test retrieving full order details by reference code."""
    with app.app_context():
        order = Order(
            order_reference="ORD-DETAILS-CHECK",
            customer_name="Deepa",
            customer_email="deepa@example.com",
            customer_phone="9876543210",
            delivery_address="Suite 100",
            city="Hyderabad",
            postal_code="500001",
            subtotal=89.99,
            delivery_fee=5.0,
            total_amount=94.99,
            status="CONFIRMED",
        )
        db.session.add(order)
        db.session.flush()

        item = OrderItem(
            order_id=order.id,
            product_id=1,
            product_name="Ultra-Slim Wireless Mechanical Keyboard",
            unit_price=89.99,
            quantity=1,
            line_total=89.99,
        )
        db.session.add(item)
        db.session.commit()

    response = client.get("/api/admin/orders/ORD-DETAILS-CHECK", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["order"]["customer_name"] == "Deepa"
    assert len(data["order"]["items"]) == 1
    assert data["order"]["items"][0]["product_name"] == "Ultra-Slim Wireless Mechanical Keyboard"


def test_admin_update_order_status(client, admin_headers, app):
    """Test updating order fulfillment status."""
    with app.app_context():
        order = Order(
            order_reference="ORD-STATUS-TEST",
            customer_name="Ramesh",
            customer_email="ramesh@example.com",
            customer_phone="9876543210",
            delivery_address="Main Road",
            city="Kochi",
            postal_code="682001",
            subtotal=69.99,
            delivery_fee=5.0,
            total_amount=74.99,
            status="CONFIRMED",
        )
        db.session.add(order)
        db.session.commit()

    # Update to SHIPPED
    res1 = client.patch(
        "/api/admin/orders/ORD-STATUS-TEST/status",
        headers=admin_headers,
        json={"status": "SHIPPED"}
    )
    assert res1.status_code == 200
    assert res1.get_json()["order"]["status"] == "SHIPPED"

    # Update to DELIVERED
    res2 = client.patch(
        "/api/admin/orders/ORD-STATUS-TEST/status",
        headers=admin_headers,
        json={"status": "DELIVERED"}
    )
    assert res2.status_code == 200
    assert res2.get_json()["order"]["status"] == "DELIVERED"

    # Reject invalid backwards transition from DELIVERED to PENDING
    res_back = client.patch(
        "/api/admin/orders/ORD-STATUS-TEST/status",
        headers=admin_headers,
        json={"status": "PENDING"}
    )
    assert res_back.status_code == 400
    assert "Cannot transition order" in res_back.get_json()["error"]

    # Reject transition from DELIVERED to SHIPPED
    res_shipped_again = client.patch(
        "/api/admin/orders/ORD-STATUS-TEST/status",
        headers=admin_headers,
        json={"status": "SHIPPED"}
    )
    assert res_shipped_again.status_code == 400
    assert "Cannot transition order" in res_shipped_again.get_json()["error"]

    # Allow idempotent update (DELIVERED to DELIVERED)
    res_idempotent = client.patch(
        "/api/admin/orders/ORD-STATUS-TEST/status",
        headers=admin_headers,
        json={"status": "DELIVERED"}
    )
    assert res_idempotent.status_code == 200
    assert res_idempotent.get_json()["order"]["status"] == "DELIVERED"

    # Reject invalid status name
    res_bad = client.patch(
        "/api/admin/orders/ORD-STATUS-TEST/status",
        headers=admin_headers,
        json={"status": "UNRECOGNIZED_STATUS"}
    )
    assert res_bad.status_code == 400
    assert "error" in res_bad.get_json()


def test_order_status_state_machine_transitions(client, admin_headers, app):
    """Test full matrix of allowed and forbidden order status state transitions."""
    with app.app_context():
        order1 = Order(
            order_reference="ORD-TRANS-PENDING",
            customer_name="Pooja",
            customer_email="pooja@example.com",
            customer_phone="9876543210",
            delivery_address="Flat 2B",
            city="Pune",
            postal_code="411001",
            subtotal=50.0,
            delivery_fee=5.0,
            total_amount=55.0,
            status="PENDING",
        )
        order2 = Order(
            order_reference="ORD-TRANS-CANCELLED",
            customer_name="Ravi",
            customer_email="ravi@example.com",
            customer_phone="9876543210",
            delivery_address="Plot 5",
            city="Jaipur",
            postal_code="302001",
            subtotal=50.0,
            delivery_fee=5.0,
            total_amount=55.0,
            status="CANCELLED",
        )
        db.session.add_all([order1, order2])
        db.session.commit()

    # 1. PENDING -> CONFIRMED is allowed
    r1 = client.patch(
        "/api/admin/orders/ORD-TRANS-PENDING/status",
        headers=admin_headers,
        json={"status": "CONFIRMED"}
    )
    assert r1.status_code == 200
    assert r1.get_json()["order"]["status"] == "CONFIRMED"

    # 2. CONFIRMED -> PENDING is forbidden
    r2 = client.patch(
        "/api/admin/orders/ORD-TRANS-PENDING/status",
        headers=admin_headers,
        json={"status": "PENDING"}
    )
    assert r2.status_code == 400
    assert "Cannot transition order" in r2.get_json()["error"]

    # 3. CANCELLED -> CONFIRMED is forbidden (terminal state)
    r3 = client.patch(
        "/api/admin/orders/ORD-TRANS-CANCELLED/status",
        headers=admin_headers,
        json={"status": "CONFIRMED"}
    )
    assert r3.status_code == 400
    assert "Cannot transition order from 'CANCELLED'" in r3.get_json()["error"]

    # 4. CANCELLED -> SHIPPED is forbidden
    r4 = client.patch(
        "/api/admin/orders/ORD-TRANS-CANCELLED/status",
        headers=admin_headers,
        json={"status": "SHIPPED"}
    )
    assert r4.status_code == 400

    # 5. CANCELLED -> CANCELLED (idempotent) is allowed
    r5 = client.patch(
        "/api/admin/orders/ORD-TRANS-CANCELLED/status",
        headers=admin_headers,
        json={"status": "CANCELLED"}
    )
    assert r5.status_code == 200


def test_admin_password_rotation_invalidates_session(client, app, admin_user):
    """Test that rotating an administrator's password immediately invalidates active session tokens."""
    from rotate_admin_password import rotate_admin_password

    # 1. Obtain token with original password
    with app.app_context():
        admin = db.session.get(Admin, admin_user)
        token = AuthService.generate_token(admin)
        headers = {"Authorization": f"Bearer {token}"}

    # Verify initial token works
    res_initial = client.get("/api/admin/me", headers=headers)
    assert res_initial.status_code == 200

    # 2. Rotate the administrator's password
    with app.app_context():
        rotate_admin_password("superadmin", "BrandNewSecurePassword456!")

    # 3. Verify previous token is now rejected with 401 Unauthorized
    res_after_rotation = client.get("/api/admin/me", headers=headers)
    assert res_after_rotation.status_code == 401
    err = res_after_rotation.get_json()["error"].lower()
    assert "invalid" in err or "revoked" in err or "expired" in err

    # 4. Verify old password cannot log in
    res_old_login = client.post("/api/admin/login", json={
        "username": "superadmin",
        "password": "AdminSecurePass123!"
    })
    assert res_old_login.status_code == 401

    # 5. Verify new password can log in and receives fresh working session via cookie
    res_new_login = client.post("/api/admin/login", json={
        "username": "superadmin",
        "password": "BrandNewSecurePassword456!"
    })
    assert res_new_login.status_code == 200
    assert "token" not in res_new_login.get_json()
    assert "admin_session=" in res_new_login.headers.get("Set-Cookie", "")

    # Fresh session works via cookie
    res_fresh = client.get("/api/admin/me")
    assert res_fresh.status_code == 200
