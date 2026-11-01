import pytest
from app.database import seed_db


@pytest.fixture(autouse=True)
def populate_sample_products(app):
    """Ensure database has sample products seeded for product API tests."""
    with app.app_context():
        seed_db()


def test_list_all_products(client):
    """Test GET /api/products returns all products."""
    response = client.get("/api/products")
    assert response.status_code == 200
    data = response.get_json()
    assert "products" in data
    assert data["count"] >= 10
    product = data["products"][0]
    for key in ("id", "name", "description", "category", "price", "stock_quantity"):
        assert key in product


def test_search_products_by_name(client):
    """Test searching products by name substring."""
    response = client.get("/api/products?search=Keyboard")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] >= 1
    assert all("keyboard" in p["name"].lower() for p in data["products"])


def test_search_products_no_match(client):
    """Test searching with term that matches no products."""
    response = client.get("/api/products?search=NonExistentItemXYZ")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 0
    assert len(data["products"]) == 0


def test_filter_products_by_category(client):
    """Test filtering products by category."""
    response = client.get("/api/products?category=Audio")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] > 0
    assert all(p["category"] == "Audio" for p in data["products"])


def test_filter_products_by_category_case_insensitive(client):
    """Test filtering category is case-insensitive."""
    response = client.get("/api/products?category=electronics")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] > 0
    assert all(p["category"] == "Electronics" for p in data["products"])


def test_filter_products_by_price_range(client):
    """Test filtering by min_price and max_price."""
    response = client.get("/api/products?min_price=40&max_price=80")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] > 0
    assert all(40 <= p["price"] <= 80 for p in data["products"])


def test_sort_products_price_asc(client):
    """Test sorting products by price ascending."""
    response = client.get("/api/products?sort=price_asc")
    assert response.status_code == 200
    data = response.get_json()
    prices = [p["price"] for p in data["products"]]
    assert prices == sorted(prices)


def test_sort_products_price_desc(client):
    """Test sorting products by price descending."""
    response = client.get("/api/products?sort=price_desc")
    assert response.status_code == 200
    data = response.get_json()
    prices = [p["price"] for p in data["products"]]
    assert prices == sorted(prices, reverse=True)


def test_sort_products_name_asc(client):
    """Test sorting products by name ascending."""
    response = client.get("/api/products?sort=name_asc")
    assert response.status_code == 200
    data = response.get_json()
    names = [p["name"] for p in data["products"]]
    assert names == sorted(names)


def test_sort_products_name_desc(client):
    """Test sorting products by name descending."""
    response = client.get("/api/products?sort=name_desc")
    assert response.status_code == 200
    data = response.get_json()
    names = [p["name"] for p in data["products"]]
    assert names == sorted(names, reverse=True)


def test_combined_filters_and_sort(client):
    """Test combining category, price range, and sort order."""
    response = client.get("/api/products?category=Electronics&min_price=30&max_price=100&sort=price_asc")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] > 0
    for p in data["products"]:
        assert p["category"] == "Electronics"
        assert 30 <= p["price"] <= 100
    prices = [p["price"] for p in data["products"]]
    assert prices == sorted(prices)


def test_invalid_price_parameters(client):
    """Test validation errors for invalid price parameters."""
    # Negative min_price
    r1 = client.get("/api/products?min_price=-10")
    assert r1.status_code == 400
    assert "error" in r1.get_json()

    # Non-numeric max_price
    r2 = client.get("/api/products?max_price=abc")
    assert r2.status_code == 400
    assert "error" in r2.get_json()

    # min_price > max_price
    r3 = client.get("/api/products?min_price=100&max_price=50")
    assert r3.status_code == 400
    assert "error" in r3.get_json()

    # Invalid sort parameter
    r4 = client.get("/api/products?sort=random_sort")
    assert r4.status_code == 400
    assert "error" in r4.get_json()


def test_get_product_by_id_success(client):
    """Test GET /api/products/<id> returns product details."""
    response = client.get("/api/products/1")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == 1
    assert "name" in data
    assert "price" in data
    assert "stock_quantity" in data
    assert "description" in data


def test_get_product_by_id_not_found(client):
    """Test GET /api/products/<id> with non-existent ID returns 404."""
    response = client.get("/api/products/99999")
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data


def test_get_categories(client):
    """Test GET /api/categories returns category list with counts."""
    response = client.get("/api/categories")
    assert response.status_code == 200
    data = response.get_json()
    assert "categories" in data
    assert len(data["categories"]) >= 3
    for cat in data["categories"]:
        assert "name" in cat
        assert "count" in cat
        assert cat["count"] > 0
