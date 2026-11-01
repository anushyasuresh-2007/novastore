import logging
from app.models.db import db
from app.models.product import Product
from app.models.order import Order
from app.models.order_item import OrderItem

logger = logging.getLogger(__name__)

SAMPLE_PRODUCTS = [
    {
        "name": "Ultra-Slim Wireless Mechanical Keyboard",
        "description": "Low-profile mechanical switches with RGB backlighting, Bluetooth 5.3, and multi-device pairing.",
        "category": "Electronics",
        "price": 89.99,
        "stock_quantity": 25,
        "image_path": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "Precision Ergonomic Optical Mouse",
        "description": "Contoured ergonomic wireless mouse with silent clicks, rechargeable battery, and adjustable DPI.",
        "category": "Electronics",
        "price": 49.50,
        "stock_quantity": 40,
        "image_path": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "4K Ultra-HD Webcam with Dual Mics",
        "description": "Crystal clear 4K 60fps streaming webcam with auto-focus and AI background noise reduction.",
        "category": "Electronics",
        "price": 79.99,
        "stock_quantity": 18,
        "image_path": "https://images.unsplash.com/photo-1587826080692-f439cd0b70da?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "Noise-Cancelling Wireless Headphones",
        "description": "Industry-leading active noise cancellation, 40-hour battery life, and high-fidelity sound.",
        "category": "Audio",
        "price": 199.99,
        "stock_quantity": 15,
        "image_path": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "Studio Reference Desktop Speakers",
        "description": "Compact powered monitor speakers with crisp highs, balanced mid-range, and deep bass response.",
        "category": "Audio",
        "price": 149.00,
        "stock_quantity": 12,
        "image_path": "https://images.unsplash.com/photo-1545454675-3531b543be5d?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "True Wireless Sport Earbuds",
        "description": "IPX7 waterproof wireless earbuds with secure ear hooks and 28-hour playtime charging case.",
        "category": "Audio",
        "price": 69.99,
        "stock_quantity": 30,
        "image_path": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "Pro Fitness Smartwatch",
        "description": "AMOLED touch display, 24/7 heart-rate and SpO2 tracking, GPS, and 14-day battery life.",
        "category": "Wearables",
        "price": 129.99,
        "stock_quantity": 20,
        "image_path": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "Smart Activity Tracker Band",
        "description": "Lightweight fitness wristband featuring step counting, sleep analysis, and water resistance up to 50m.",
        "category": "Wearables",
        "price": 39.99,
        "stock_quantity": 50,
        "image_path": "https://images.unsplash.com/photo-1575311373937-040b8e1fd5b6?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "Adjustable Aluminum Laptop Stand",
        "description": "Ventilated foldable aluminum riser supporting laptops up to 17 inches for improved posture.",
        "category": "Home & Office",
        "price": 34.99,
        "stock_quantity": 35,
        "image_path": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "Smart LED Desk Lamp with Wireless Charger",
        "description": "Dimmable eye-care LED lamp with 5 color temperatures, timer, and fast Qi wireless charging pad.",
        "category": "Home & Office",
        "price": 54.99,
        "stock_quantity": 22,
        "image_path": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "Full-Desk Anti-Slip Mouse Mat",
        "description": "Extended waterproof gaming and office desk pad with stitched anti-fray edges (900x400mm).",
        "category": "Home & Office",
        "price": 24.99,
        "stock_quantity": 45,
        "image_path": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "High-Speed 100W GaN Fast Charger",
        "description": "Compact 3-port USB-C and USB-A GaN wall charger capable of fast-charging laptops, tablets, and phones.",
        "category": "Accessories",
        "price": 45.00,
        "stock_quantity": 60,
        "image_path": "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?auto=format&fit=crop&w=600&q=80",
    },
]


def init_db(drop_all: bool = False):
    """Create all database tables, optionally dropping existing tables first."""
    if drop_all:
        logger.info("Dropping all existing database tables...")
        db.drop_all()
    logger.info("Creating database tables...")
    db.create_all()


def seed_db():
    """Seed the database with sample products using transaction management."""
    init_db(drop_all=False)

    existing_count = Product.query.count()
    if existing_count > 0:
        logger.info(f"Database already contains {existing_count} products. Skipping seeding.")
        return existing_count

    try:
        products = [Product(**item) for item in SAMPLE_PRODUCTS]
        db.session.bulk_save_objects(products)
        db.session.commit()
        logger.info(f"Successfully seeded {len(products)} products into the database.")
        return len(products)
    except Exception as exc:
        db.session.rollback()
        logger.error(f"Error seeding database: {exc}")
        raise exc
