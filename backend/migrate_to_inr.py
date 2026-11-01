"""Safe, additive SQLite migration script to introduce INR currency support."""
import os
import sys
import sqlite3

APPROVED_INR_PRICES = {
    1: 6999.0,
    2: 3799.0,
    3: 5999.0,
    4: 14999.0,
    5: 11999.0,
    6: 4999.0,
    7: 9999.0,
    8: 2999.0,
    9: 2499.0,
    10: 3999.0,
    11: 1499.0,
    12: 3499.0,
    13: 74999.0,
    14: 9999.0,
    15: 5499.0,
    16: 15999.0,
    17: 12999.0,
    18: 1299.0,
    19: 3299.0,
    20: 6499.0,
    21: 4499.0,
    22: 8999.0,
    23: 2999.0,
    24: 999.0,
    25: 1499.0,
    26: 18999.0,
    27: 5999.0,
    28: 1299.0,
    29: 3499.0,
    30: 17999.0,
}


def get_column_names(cursor, table_name: str):
    """Retrieve column names for a table."""
    return [col[1] for col in cursor.execute(f"PRAGMA table_info({table_name})").fetchall()]


def run_migration(db_path: str):
    print(f"Connecting to database: {db_path}")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found at: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check current tables
        tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print("Existing tables:", tables)
        for required_table in ["products", "orders", "order_items"]:
            if required_table not in tables:
                raise RuntimeError(f"Missing required table: {required_table}")

        # Record pre-migration state of historical orders
        pre_orders = cursor.execute(
            "SELECT id, order_reference, customer_name, subtotal, delivery_fee, total_amount, status FROM orders ORDER BY id ASC"
        ).fetchall()
        print(f"Found {len(pre_orders)} historical order(s) before migration:")
        for o in pre_orders:
            print("  Pre-order:", o)

        pre_items = cursor.execute(
            "SELECT id, order_id, product_id, product_name, unit_price, quantity, line_total FROM order_items ORDER BY id ASC"
        ).fetchall()
        print(f"Found {len(pre_items)} historical order item(s) before migration:")
        for it in pre_items:
            print("  Pre-item:", it)

        # Record pre-migration stock quantities
        pre_stock = {
            r[0]: r[1] for r in cursor.execute("SELECT id, stock_quantity FROM products ORDER BY id ASC").fetchall()
        }

        # 1. Add currency column to products if not exists
        product_cols = get_column_names(cursor, "products")
        if "currency" not in product_cols:
            print("Adding 'currency' column to 'products' table...")
            cursor.execute("ALTER TABLE products ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'INR'")
        else:
            print("'currency' column already exists on 'products'.")

        # 2. Add currency column to orders if not exists
        order_cols = get_column_names(cursor, "orders")
        if "currency" not in order_cols:
            print("Adding 'currency' column to 'orders' table...")
            cursor.execute("ALTER TABLE orders ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'INR'")
        else:
            print("'currency' column already exists on 'orders'.")

        # 3. Add currency column to order_items if not exists
        item_cols = get_column_names(cursor, "order_items")
        if "currency" not in item_cols:
            print("Adding 'currency' column to 'order_items' table...")
            cursor.execute("ALTER TABLE order_items ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'INR'")
        else:
            print("'currency' column already exists on 'order_items'.")

        # 4. Tag existing historical orders and historical order items with currency = 'USD'
        for o in pre_orders:
            order_id = o[0]
            print(f"Tagging historical order #{order_id} ({o[1]}) as USD...")
            cursor.execute("UPDATE orders SET currency = 'USD' WHERE id = ?", (order_id,))
            cursor.execute("UPDATE order_items SET currency = 'USD' WHERE order_id = ?", (order_id,))

        # 5. Update 30 existing products with approved INR prices and currency = 'INR'
        print("Updating 30 products with approved INR prices...")
        for pid, inr_price in APPROVED_INR_PRICES.items():
            cursor.execute(
                "UPDATE products SET price = ?, currency = 'INR' WHERE id = ?",
                (inr_price, pid)
            )

        conn.commit()
        print("Database transaction successfully committed!")

        # 6. Post-migration verification
        print("\n--- POST-MIGRATION VERIFICATION ---")

        # Verify historical orders
        post_orders = cursor.execute(
            "SELECT id, order_reference, customer_name, subtotal, delivery_fee, total_amount, status, currency FROM orders ORDER BY id ASC"
        ).fetchall()
        print(f"Verified {len(post_orders)} historical order(s):")
        for o in post_orders:
            print("  Post-order:", o)
            assert o[7] == "USD", f"Expected USD currency on historical order #{o[0]}, got {o[7]}"

        # Verify historical items
        post_items = cursor.execute(
            "SELECT id, order_id, product_id, product_name, unit_price, quantity, line_total, currency FROM order_items ORDER BY id ASC"
        ).fetchall()
        print(f"Verified {len(post_items)} historical item(s):")
        for it in post_items:
            print("  Post-item:", it)
            assert it[7] == "USD", f"Expected USD currency on historical item #{it[0]}, got {it[7]}"

        # Verify historical order monetary amounts were completely preserved
        for pre, post in zip(pre_orders, post_orders):
            assert pre[0] == post[0]  # ID
            assert pre[1] == post[1]  # Reference
            assert pre[3] == post[3]  # Subtotal
            assert pre[4] == post[4]  # Delivery Fee
            assert pre[5] == post[5]  # Total Amount
            assert pre[6] == post[6]  # Status

        for pre, post in zip(pre_items, post_items):
            assert pre[0] == post[0]  # ID
            assert pre[1] == post[1]  # Order ID
            assert pre[4] == post[4]  # Unit Price
            assert pre[5] == post[5]  # Qty
            assert pre[6] == post[6]  # Line Total

        # Verify products
        post_products = cursor.execute(
            "SELECT id, name, category, price, stock_quantity, currency, is_active FROM products ORDER BY id ASC"
        ).fetchall()
        assert len(post_products) == 30, f"Expected 30 products, got {len(post_products)}"
        print(f"\nVerified {len(post_products)} products:")
        for p in post_products:
            pid = p[0]
            expected_price = APPROVED_INR_PRICES[pid]
            assert p[3] == expected_price, f"Product #{pid} price mismatch: expected {expected_price}, got {p[3]}"
            assert p[5] == "INR", f"Product #{pid} currency mismatch: expected 'INR', got {p[5]}"
            assert p[4] == pre_stock[pid], f"Product #{pid} stock quantity changed! Was {pre_stock[pid]}, now {p[4]}"
            print(f"  #{p[0]:2d} | {p[1]:<45} | {p[2]:<15} | INR {p[3]:>7.0f} | Stock: {p[4]:2d} | Curr: {p[5]}")

        print("\nALL POST-MIGRATION CHECKS PASSED WITH 100% INTEGRITY!")

    finally:
        conn.close()


if __name__ == "__main__":
    db_file = os.path.abspath("instance/store.db")
    run_migration(db_file)
