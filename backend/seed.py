"""Standalone script to initialize and seed the database."""
import os
import sys

# Ensure backend directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app import create_app
from app.database import init_db, seed_db

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        print("Initializing database...")
        init_db()
        print("Seeding sample products...")
        count = seed_db()
        print(f"Done! {count} products available in database.")
