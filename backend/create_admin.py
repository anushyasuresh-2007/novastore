"""Standalone script to create or update an administrator account securely."""
import os
import sys
import argparse
import getpass

# Ensure backend directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app import create_app
from app.models.db import db
from app.models.admin import Admin
from app.database import init_db


MIN_ADMIN_PASSWORD_LENGTH = 8


def create_or_update_admin(username: str, email: str, password: str, role: str = "admin") -> Admin:
    """Create a new admin or update existing admin's password securely."""
    if not username or len(username) < 3:
        raise ValueError("Username must be at least 3 characters.")
    if not email or "@" not in email:
        raise ValueError("Valid email address is required.")
    if not password or len(password) < MIN_ADMIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_ADMIN_PASSWORD_LENGTH} characters.")

    existing = Admin.query.filter(
        (Admin.username == username.strip()) | (Admin.email == email.strip().lower())
    ).first()

    if existing:
        existing.username = username.strip()
        existing.email = email.strip().lower()
        existing.role = role
        existing.is_active = True
        existing.set_password(password)
        db.session.commit()
        print(f"Updated existing administrator '{existing.username}' (ID #{existing.id}).")
        return existing
    else:
        admin = Admin(
            username=username.strip(),
            email=email.strip().lower(),
            role=role,
            is_active=True,
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Created new administrator '{admin.username}' (ID #{admin.id}).")
        return admin


def main():
    parser = argparse.ArgumentParser(description="Create or update Novastore Administrator account.")
    parser.add_argument("--username", help="Admin username (or env: ADMIN_USERNAME)")
    parser.add_argument("--email", help="Admin email address (or env: ADMIN_EMAIL)")
    parser.add_argument("--password", help="[Discouraged] Admin password (prefer interactive prompt or ADMIN_PASSWORD env var)")
    parser.add_argument("--role", default="admin", help="Admin role (default: admin)")
    args = parser.parse_args()

    username = args.username or os.environ.get("ADMIN_USERNAME")
    email = args.email or os.environ.get("ADMIN_EMAIL")
    password = args.password or os.environ.get("ADMIN_PASSWORD")

    if args.password:
        print(
            "[SECURITY WARNING] Passing passwords via CLI arguments exposes them in process lists "
            "and shell history. Prefer interactive entry or ADMIN_PASSWORD environment variable.",
            file=sys.stderr
        )

    # If parameters not provided via flags or env, prompt interactively
    if not username:
        username = input("Admin username: ").strip()
    if not email:
        email = input("Admin email: ").strip().lower()
    if not password:
        while True:
            password = getpass.getpass(f"Admin password (min {MIN_ADMIN_PASSWORD_LENGTH} chars): ")
            if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
                print(f"Error: Password must be at least {MIN_ADMIN_PASSWORD_LENGTH} characters.")
                continue
            confirm = getpass.getpass("Confirm admin password: ")
            if password != confirm:
                print("Error: Passwords do not match. Please try again.")
                continue
            break

    app = create_app()
    with app.app_context():
        init_db()
        create_or_update_admin(username, email, password, args.role)


if __name__ == "__main__":
    main()
