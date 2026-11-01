import pytest
from sqlalchemy.exc import IntegrityError
from app.models.product import Product
from app.models.order import Order
from app.models.order_item import OrderItem


def test_product_model_creation(app, db_session):
    """Test creating and serializing a Product."""
    with app.app_context():
        p = Product(
            name="Mechanical Keyboard",
            description="RGB mechanical switches",
            category="Electronics",
            price=99.99,
            stock_quantity=15,
            image_path="keyboard.jpg"
        )
        db_session.add(p)
        db_session.commit()

        assert p.id is not None
        d = p.to_dict()
        assert d["name"] == "Mechanical Keyboard"
        assert d["price"] == 99.99
        assert d["stock_quantity"] == 15
        assert d["created_at"] is not None


def test_product_negative_stock_constraint(app, db_session):
    """Test negative stock violates check constraint."""
    with app.app_context():
        p = Product(
            name="Bad Stock Product",
            description="Testing negative stock",
            category="Test",
            price=10.0,
            stock_quantity=-1
        )
        db_session.add(p)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


def test_order_and_order_item_snapshot(app, db_session):
    """Test Order and OrderItem creation preserves snapshot values."""
    with app.app_context():
        # Create product
        p = Product(
            name="Wireless Mouse",
            description="Ergonomic mouse",
            category="Electronics",
            price=39.99,
            stock_quantity=20
        )
        db_session.add(p)
        db_session.commit()

        # Create order
        order = Order(
            order_reference="ORD-TEST-1001",
            customer_name="Jane Doe",
            customer_email="jane@example.com",
            customer_phone="1234567890",
            delivery_address="123 Main St",
            city="Metropolis",
            postal_code="10001",
            subtotal=79.98,
            delivery_fee=5.00,
            total_amount=84.98,
            status="CONFIRMED"
        )
        db_session.add(order)
        db_session.flush()

        # Create order item with purchase-time snapshot
        item = OrderItem(
            order_id=order.id,
            product_id=p.id,
            product_name=p.name,
            unit_price=p.price,
            quantity=2,
            line_total=round(p.price * 2, 2)
        )
        db_session.add(item)
        db_session.commit()

        # Even if original product changes price/name, order item retains snapshot
        p.price = 49.99
        p.name = "Wireless Mouse v2"
        db_session.commit()

        refreshed_order = Order.query.filter_by(order_reference="ORD-TEST-1001").first()
        assert refreshed_order is not None
        assert len(refreshed_order.items) == 1

        order_dict = refreshed_order.to_dict(include_items=True)
        assert order_dict["customer_name"] == "Jane Doe"
        assert order_dict["items"][0]["product_name"] == "Wireless Mouse"
        assert order_dict["items"][0]["unit_price"] == 39.99
        assert order_dict["items"][0]["quantity"] == 2
        assert order_dict["items"][0]["line_total"] == 79.98


def test_order_cascade_delete(app, db_session):
    """Test deleting an order cascades and deletes its order items."""
    with app.app_context():
        p = Product(
            name="Cascade Test Item",
            description="Testing cascade delete",
            category="Electronics",
            price=15.0,
            stock_quantity=10
        )
        db_session.add(p)
        db_session.commit()

        order = Order(
            order_reference="ORD-CASCADE-1",
            customer_name="Test User",
            customer_email="test@user.com",
            customer_phone="5551234",
            delivery_address="456 Elm St",
            city="Springfield",
            postal_code="90210",
            subtotal=15.0,
            delivery_fee=0.0,
            total_amount=15.0
        )
        db_session.add(order)
        db_session.flush()

        item = OrderItem(
            order_id=order.id,
            product_id=p.id,
            product_name=p.name,
            unit_price=p.price,
            quantity=1,
            line_total=15.0
        )
        db_session.add(item)
        db_session.commit()

        assert OrderItem.query.filter_by(order_id=order.id).count() == 1

        # Delete order
        db_session.delete(order)
        db_session.commit()

        assert OrderItem.query.filter_by(order_id=order.id).count() == 0
        # Product should still exist
        assert db_session.get(Product, p.id) is not None
