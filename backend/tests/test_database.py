import pytest
from sqlalchemy.exc import IntegrityError
from app.database import seed_db
from app.models.product import Product
from app.models.order import Order
from app.models.order_item import OrderItem


def test_health_check(client):
    """Test health check route returns healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_seed_database(app, db_session):
    """Test seed_db populates products table."""
    with app.app_context():
        count = seed_db()
        assert count >= 10
        products = Product.query.all()
        assert len(products) == count

        # Verify multiple categories exist
        categories = {p.category for p in products}
        assert len(categories) >= 3


def test_seed_database_idempotent(app, db_session):
    """Test running seed_db multiple times does not duplicate products."""
    with app.app_context():
        count1 = seed_db()
        count2 = seed_db()
        assert count1 == count2
        assert Product.query.count() == count1


def test_database_transaction_rollback_on_error(app, db_session):
    """Test database rollback restores state when an error occurs."""
    with app.app_context():
        # Add a valid product
        p = Product(
            name="Valid Product",
            description="A valid test product",
            category="Test",
            price=19.99,
            stock_quantity=10,
        )
        db_session.add(p)
        db_session.commit()
        initial_count = Product.query.count()

        # Attempt adding an invalid product (negative price violation)
        try:
            invalid_p = Product(
                name="Invalid Product",
                description="Violates constraint",
                category="Test",
                price=-5.00,
                stock_quantity=5,
            )
            db_session.add(invalid_p)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()

        # Count should remain unchanged
        assert Product.query.count() == initial_count


def test_sqlite_foreign_key_enforcement(app, db_session):
    """Test SQLite foreign keys are enforced by PRAGMA."""
    with app.app_context():
        # Attempt inserting OrderItem with non-existent order_id and product_id
        item = OrderItem(
            order_id=9999,
            product_id=8888,
            product_name="Ghost Item",
            unit_price=10.0,
            quantity=1,
            line_total=10.0,
        )
        db_session.add(item)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
