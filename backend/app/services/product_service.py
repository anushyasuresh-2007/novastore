from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import func
from app.models.db import db
from app.models.product import Product


class ProductService:
    """Service handling product catalog queries, filtering, and retrieval."""

    SORT_OPTIONS = {
        "price_asc": Product.price.asc(),
        "price_desc": Product.price.desc(),
        "name_asc": Product.name.asc(),
        "name_desc": Product.name.desc(),
        "newest": Product.created_at.desc(),
    }

    @classmethod
    def get_products(
        cls,
        search: Optional[str] = None,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        sort_by: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[Product]:
        """
        Query products applying optional search, category, price range, and sort orders.
        """
        query = Product.query

        if not include_inactive:
            query = query.filter(Product.is_active == True)

        # Search by product name (case-insensitive substring match)
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(Product.name.ilike(term))

        # Filter by category (case-insensitive)
        if category and category.strip() and category.strip().lower() != "all":
            query = query.filter(func.lower(Product.category) == category.strip().lower())

        # Filter by minimum price
        if min_price is not None:
            query = query.filter(Product.price >= min_price)

        # Filter by maximum price
        if max_price is not None:
            query = query.filter(Product.price <= max_price)

        # Apply sorting
        order_clause = cls.SORT_OPTIONS.get(sort_by, Product.id.asc())
        query = query.order_by(order_clause)

        return query.all()

    @classmethod
    def get_product_by_id(cls, product_id: int, include_inactive: bool = False) -> Optional[Product]:
        """Fetch a single product by its primary key ID."""
        product = db.session.get(Product, product_id)
        if product and not include_inactive and not product.is_active:
            return None
        return product

    @classmethod
    def get_categories(cls, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Return list of distinct categories with product counts."""
        query = db.session.query(
            Product.category,
            func.count(Product.id).label("count")
        )
        if not include_inactive:
            query = query.filter(Product.is_active == True)

        results = query.group_by(Product.category).order_by(Product.category.asc()).all()
        return [{"name": cat, "count": count} for cat, count in results]

