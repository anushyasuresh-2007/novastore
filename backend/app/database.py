import os
import logging
from sqlalchemy import text
from app.models.db import db
from app.models.product import Product
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.admin import Admin

logger = logging.getLogger(__name__)

SAMPLE_PRODUCTS = [
    # 1. Electronics
    {
        "name": "Ultra-Slim Wireless Mechanical Keyboard",
        "description": "Low-profile mechanical switches with RGB backlighting, Bluetooth 5.3, and multi-device pairing.",
        "category": "Electronics",
        "price": 6999.00,
        "currency": "INR",
        "stock_quantity": 25,
        "image_path": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=600&q=80",
    },
    # 2. Electronics
    {
        "name": "Precision Ergonomic Optical Mouse",
        "description": "Contoured ergonomic wireless mouse with silent clicks, rechargeable battery, and adjustable DPI.",
        "category": "Electronics",
        "price": 3799.00,
        "currency": "INR",
        "stock_quantity": 40,
        "image_path": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?auto=format&fit=crop&w=600&q=80",
    },
    # 3. Electronics
    {
        "name": "4K Ultra-HD Webcam with Dual Mics",
        "description": "Crystal clear 4K 60fps streaming webcam with auto-focus and AI background noise reduction.",
        "category": "Electronics",
        "price": 5999.00,
        "currency": "INR",
        "stock_quantity": 18,
        "image_path": "https://images.unsplash.com/photo-1587826080692-f439cd0b70da?auto=format&fit=crop&w=600&q=80",
    },
    # 4. Audio
    {
        "name": "Noise-Cancelling Wireless Headphones",
        "description": "Industry-leading active noise cancellation, 40-hour battery life, and high-fidelity sound.",
        "category": "Audio",
        "price": 14999.00,
        "currency": "INR",
        "stock_quantity": 15,
        "image_path": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&q=80",
    },
    # 5. Audio
    {
        "name": "Studio Reference Desktop Speakers",
        "description": "Compact powered monitor speakers with crisp highs, balanced mid-range, and deep bass response.",
        "category": "Audio",
        "price": 11999.00,
        "currency": "INR",
        "stock_quantity": 12,
        "image_path": "https://images.unsplash.com/photo-1545454675-3531b543be5d?auto=format&fit=crop&w=600&q=80",
    },
    # 6. Audio
    {
        "name": "True Wireless Sport Earbuds",
        "description": "IPX7 waterproof wireless earbuds with secure ear hooks and 28-hour playtime charging case.",
        "category": "Audio",
        "price": 4999.00,
        "currency": "INR",
        "stock_quantity": 30,
        "image_path": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=600&q=80",
    },
    # 7. Wearables
    {
        "name": "Pro Fitness Smartwatch",
        "description": "AMOLED touch display, 24/7 heart-rate and SpO2 tracking, GPS, and 14-day battery life.",
        "category": "Wearables",
        "price": 9999.00,
        "currency": "INR",
        "stock_quantity": 20,
        "image_path": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80",
    },
    # 8. Wearables
    {
        "name": "Smart Activity Tracker Band",
        "description": "Lightweight fitness wristband featuring step counting, sleep analysis, and water resistance up to 50m.",
        "category": "Wearables",
        "price": 2999.00,
        "currency": "INR",
        "stock_quantity": 50,
        "image_path": "https://images.unsplash.com/photo-1575311373937-040b8e1fd5b6?auto=format&fit=crop&w=600&q=80",
    },
    # 9. Home & Office
    {
        "name": "Adjustable Aluminum Laptop Stand",
        "description": "Ventilated foldable aluminum riser supporting laptops up to 17 inches for improved posture.",
        "category": "Home & Office",
        "price": 2499.00,
        "currency": "INR",
        "stock_quantity": 35,
        "image_path": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=600&q=80",
    },
    # 10. Home & Office
    {
        "name": "Smart LED Desk Lamp with Wireless Charger",
        "description": "Dimmable eye-care LED lamp with 5 color temperatures, timer, and fast Qi wireless charging pad.",
        "category": "Home & Office",
        "price": 3999.00,
        "currency": "INR",
        "stock_quantity": 22,
        "image_path": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=600&q=80",
    },
    # 11. Home & Office
    {
        "name": "Full-Desk Anti-Slip Mouse Mat",
        "description": "Extended waterproof gaming and office desk pad with stitched anti-fray edges (900x400mm).",
        "category": "Home & Office",
        "price": 1499.00,
        "currency": "INR",
        "stock_quantity": 45,
        "image_path": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=600&q=80",
    },
    # 12. Accessories
    {
        "name": "High-Speed 100W GaN Fast Charger",
        "description": "Compact 3-port USB-C and USB-A GaN wall charger capable of fast-charging laptops, tablets, and phones.",
        "category": "Accessories",
        "price": 3499.00,
        "currency": "INR",
        "stock_quantity": 60,
        "image_path": "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?auto=format&fit=crop&w=600&q=80",
    },
    # 13. Photography
    {
        "name": "Professional 4K Mirrorless Camera",
        "description": "24.2MP full-frame sensor, 4K 60p 10-bit video, in-body 5-axis image stabilization, and dual card slots.",
        "category": "Photography",
        "price": 74999.00,
        "currency": "INR",
        "stock_quantity": 8,
        "image_path": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=600&q=80",
    },
    # 14. Photography
    {
        "name": "Carbon Fiber Lightweight Travel Tripod",
        "description": "Ultra-sturdy 4-section carbon fiber legs with 360-degree panoramic ball head, quick-release plate, and 15kg load capacity.",
        "category": "Photography",
        "price": 9999.00,
        "currency": "INR",
        "stock_quantity": 24,
        "image_path": "https://images.unsplash.com/photo-1512790182412-b19e6d62bc39?auto=format&fit=crop&w=600&q=80",
    },
    # 15. Photography
    {
        "name": "Ultra-Bright Bi-Color LED Video Light",
        "description": "Dimmable CRI 97+ portable studio light panel with adjustable color temperature (2500K-8500K) and OLED display.",
        "category": "Photography",
        "price": 5499.00,
        "currency": "INR",
        "stock_quantity": 30,
        "image_path": "https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?auto=format&fit=crop&w=600&q=80",
    },
    # 16. Photography
    {
        "name": "50mm f/1.8 Portrait Prime Lens",
        "description": "Fast aperture compact prime lens delivering breathtaking creamy bokeh, edge-to-edge sharpness, and silent autofocus motor.",
        "category": "Photography",
        "price": 15999.00,
        "currency": "INR",
        "stock_quantity": 15,
        "image_path": "https://images.unsplash.com/photo-1617005082133-548c4dd27f35?auto=format&fit=crop&w=600&q=80",
    },
    # 17. Electronics
    {
        "name": "Portable 15.6-inch Full HD IPS Monitor",
        "description": "Ultra-slim 1080p portable external display with dual USB-C, mini HDMI, built-in dual speakers, and magnetic smart cover.",
        "category": "Electronics",
        "price": 12999.00,
        "currency": "INR",
        "stock_quantity": 16,
        "image_path": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=600&q=80",
    },
    # 18. Electronics
    {
        "name": "High-Speed USB 3.0 SD & MicroSD Card Reader",
        "description": "Aluminum dual-slot memory card reader with 5Gbps transfer rate, UHS-I support, and dual USB-A and USB-C connectors.",
        "category": "Electronics",
        "price": 1299.00,
        "currency": "INR",
        "stock_quantity": 55,
        "image_path": "https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?auto=format&fit=crop&w=600&q=80",
    },
    # 19. Electronics
    {
        "name": "Dual-Bay External NVMe M.2 SSD Enclosure",
        "description": "10Gbps USB 3.2 Gen 2 aluminum enclosure with offline cloning, tool-free installation, and thermal cooling pad.",
        "category": "Electronics",
        "price": 3299.00,
        "currency": "INR",
        "stock_quantity": 35,
        "image_path": "https://images.unsplash.com/photo-1544652478-6653e09f18a2?auto=format&fit=crop&w=600&q=80",
    },
    # 20. Audio
    {
        "name": "USB Studio Condenser Podcast Microphone",
        "description": "Cardioid studio-quality condenser mic with gain control dial, zero-latency headphone monitoring, and pop filter arm kit.",
        "category": "Audio",
        "price": 6499.00,
        "currency": "INR",
        "stock_quantity": 25,
        "image_path": "https://images.unsplash.com/photo-1590602847861-f357a9332bbc?auto=format&fit=crop&w=600&q=80",
    },
    # 21. Audio
    {
        "name": "Portable Waterproof Outdoor Bluetooth Speaker",
        "description": "Rugged IP67 dustproof and waterproof speaker with 360-degree spatial sound, punchy bass, and 20-hour playback.",
        "category": "Audio",
        "price": 4499.00,
        "currency": "INR",
        "stock_quantity": 40,
        "image_path": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?auto=format&fit=crop&w=600&q=80",
    },
    # 22. Audio
    {
        "name": "Hi-Fi DAC & Headphone Desktop Amplifier",
        "description": "High-resolution 32-bit/384kHz digital-to-analog audio converter with optical, coaxial, and USB inputs for audiophile headphones.",
        "category": "Audio",
        "price": 8999.00,
        "currency": "INR",
        "stock_quantity": 18,
        "image_path": "https://images.unsplash.com/photo-1546435770-a3e426bf472b?auto=format&fit=crop&w=600&q=80",
    },
    # 23. Accessories
    {
        "name": "8-in-1 Aluminum USB-C Multiport Hub",
        "description": "Pass-through 100W Power Delivery, 4K 60Hz HDMI output, Gigabit Ethernet, SD card reader, and 3 high-speed USB 3.0 ports.",
        "category": "Accessories",
        "price": 2999.00,
        "currency": "INR",
        "stock_quantity": 50,
        "image_path": "https://images.unsplash.com/photo-1625842268584-8f3296236761?auto=format&fit=crop&w=600&q=80",
    },
    # 24. Accessories
    {
        "name": "Braided Nylon Fast-Charging Cables (3-Pack)",
        "description": "Durable 6.6ft tangle-free nylon braided USB-C to USB-C cables supporting 60W rapid charging and 480Mbps data sync.",
        "category": "Accessories",
        "price": 999.00,
        "currency": "INR",
        "stock_quantity": 75,
        "image_path": "https://images.unsplash.com/photo-1585338107529-13afc5f02586?auto=format&fit=crop&w=600&q=80",
    },
    # 25. Accessories
    {
        "name": "Ergonomic Memory Foam Wrist Rest Set",
        "description": "Premium slow-rebound memory foam keyboard and mouse wrist cushions with anti-slip rubber base for strain relief.",
        "category": "Accessories",
        "price": 1499.00,
        "currency": "INR",
        "stock_quantity": 45,
        "image_path": "https://images.unsplash.com/photo-1595225476474-87563907a212?auto=format&fit=crop&w=600&q=80",
    },
    # 26. Home & Office
    {
        "name": "Ergonomic Breathable Mesh Executive Office Chair",
        "description": "Adjustable dynamic lumbar support, 3D armrests, reclining backrest, and silent smooth-rolling caster wheels.",
        "category": "Home & Office",
        "price": 18999.00,
        "currency": "INR",
        "stock_quantity": 10,
        "image_path": "https://images.unsplash.com/photo-1580481077195-c3a821a58875?auto=format&fit=crop&w=600&q=80",
    },
    # 27. Home & Office
    {
        "name": "Smart Ceramic Temperature Control Heated Mug",
        "description": "App-controlled self-heating 14oz mug that keeps hot beverages at your precise drinking temperature for up to 2 hours.",
        "category": "Home & Office",
        "price": 5999.00,
        "currency": "INR",
        "stock_quantity": 20,
        "image_path": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=600&q=80",
    },
    # 28. Home & Office
    {
        "name": "Cable Management Organizer Box Set",
        "description": "Flame-retardant cable hider box duo with power strip surge protector concealment and reusable cable tie straps.",
        "category": "Home & Office",
        "price": 1299.00,
        "currency": "INR",
        "stock_quantity": 60,
        "image_path": "https://images.unsplash.com/photo-1586769852044-692d6e3703f0?auto=format&fit=crop&w=600&q=80",
    },
    # 29. Wearables
    {
        "name": "Smart Sleep Mask with Ultra-Thin Bluetooth Speakers",
        "description": "100% blackout contoured eye mask with ultra-flat breathable stereo audio speakers and washable soft velvet fabric.",
        "category": "Wearables",
        "price": 3499.00,
        "currency": "INR",
        "stock_quantity": 32,
        "image_path": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=600&q=80",
    },
    # 30. Wearables
    {
        "name": "Rugged GPS Adventure Multisport Watch",
        "description": "Military-grade sapphire glass with dual-frequency GPS, topographic mapping, barometric altimeter, and solar charging.",
        "category": "Wearables",
        "price": 17999.00,
        "currency": "INR",
        "stock_quantity": 14,
        "image_path": "https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?auto=format&fit=crop&w=600&q=80",
    },
]


def ensure_schema_updates():
    """Ensure non-destructive backward-compatible schema updates."""
    try:
        with db.engine.connect() as conn:
            # Check products columns
            res_prod = conn.execute(text("PRAGMA table_info(products)")).fetchall()
            if res_prod:
                prod_cols = [r[1] for r in res_prod]
                if "is_active" not in prod_cols:
                    logger.info("Adding 'is_active' column to products table...")
                    conn.execute(text("ALTER TABLE products ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"))
                    conn.commit()
                if "currency" not in prod_cols:
                    logger.info("Adding 'currency' column to products table...")
                    conn.execute(text("ALTER TABLE products ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'INR'"))
                    conn.commit()

            # Check orders columns
            res_orders = conn.execute(text("PRAGMA table_info(orders)")).fetchall()
            if res_orders:
                order_cols = [r[1] for r in res_orders]
                if "currency" not in order_cols:
                    logger.info("Adding 'currency' column to orders table...")
                    conn.execute(text("ALTER TABLE orders ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'INR'"))
                    conn.commit()

            # Check order_items columns
            res_items = conn.execute(text("PRAGMA table_info(order_items)")).fetchall()
            if res_items:
                item_cols = [r[1] for r in res_items]
                if "currency" not in item_cols:
                    logger.info("Adding 'currency' column to order_items table...")
                    conn.execute(text("ALTER TABLE order_items ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'INR'"))
                    conn.commit()
    except Exception as exc:
        logger.warning(f"Schema update check notice: {exc}")


def init_db(drop_all: bool = False):
    """Create all database tables, optionally dropping existing tables first."""
    if drop_all:
        logger.info("Dropping all existing database tables...")
        db.drop_all()
    logger.info("Creating database tables...")
    db.create_all()
    ensure_schema_updates()


def seed_db():
    """
    Seed the database with sample products using idempotent transaction management.
    Preserves all existing products (including IDs, current stock, prices) and only
    inserts missing products. Safe to run multiple times without duplication or overwriting.
    """
    init_db(drop_all=False)

    try:
        # Check existing products by name to prevent duplicates and preserve existing records
        existing_products = {p.name: p for p in Product.query.all()}
        new_products = []

        for item in SAMPLE_PRODUCTS:
            if item["name"] not in existing_products:
                new_products.append(Product(**item))

        if new_products:
            db.session.bulk_save_objects(new_products)
            db.session.commit()
            logger.info(f"Successfully seeded {len(new_products)} new products into the database.")
        else:
            logger.info("All sample products already exist in the database. No new records inserted.")

        total_count = Product.query.count()
        return total_count
    except Exception as exc:
        db.session.rollback()
        logger.error(f"Error seeding database: {exc}")
        raise exc
