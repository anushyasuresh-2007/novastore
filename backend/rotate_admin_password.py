"""Standalone script to securely rotate an administrator's password without exposing secrets."""
import os
import sys
import argparse
import getpass
from datetime import datetime, timezone

# Ensure backend directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app import create_app
from app.models.db import db
from app.models.admin import Admin
from app.database import init_db


MIN_ADMIN_PASSWORD_LENGTH = 8


def rotate_admin_password(username: str, new_password: str) -> Admin:
    """
    Update an administrator's password and touch updated_at.
    Changing the password hash automatically revokes previously issued session tokens.
    """
    if not username:
        raise ValueError("Username or email is required.")
    if not new_password or len(new_password) < MIN_ADMIN_PASSWORD_LENGTH:
        raise ValueError(f"New password must be at least {MIN_ADMIN_PASSWORD_LENGTH} characters long.")

    clean_id = username.strip().lower()
    admin = Admin.query.filter(
        (Admin.username.ilike(clean_id)) | (Admin.email.ilike(clean_id))
    ).first()

    if not admin:
        raise LookupError(f"Administrator '{username}' not found.")

    admin.set_password(new_password)
    admin.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    print(f"Success: Password for administrator '{admin.username}' (ID #{admin.id}) has been successfully rotated.")
    print("Security note: All previously issued session tokens have been automatically revoked.")
    return admin


def main():
    parser = argparse.ArgumentParser(
        description="Securely rotate an administrator password for Novastore."
    )
    parser.add_argument(
        "--username",
        help="Admin username or email (optional if only one administrator exists)",
    )
    parser.add_argument(
        "--password",
        help="[Discouraged] New password via CLI (prefer interactive entry or NEW_ADMIN_PASSWORD env var)",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        init_db()

        username = args.username or os.environ.get("ADMIN_USERNAME")
        if not username:
            admins = Admin.query.all()
            if len(admins) == 1:
                username = admins[0].username
                print(f"Detected single administrator: '{username}'")
            elif not admins:
                print("Error: No administrators found in the database. Run create_admin.py first.", file=sys.stderr)
                sys.exit(1)
            else:
                username = input("Enter admin username or email: ").strip()

        if args.password:
            print(
                "[SECURITY WARNING] Passing passwords via CLI arguments exposes them in process lists "
                "and shell history. Prefer interactive entry or NEW_ADMIN_PASSWORD environment variable.",
                file=sys.stderr
            )

        password = args.password or os.environ.get("NEW_ADMIN_PASSWORD")
        if not password:
            while True:
                password = getpass.getpass(f"Enter new admin password (min {MIN_ADMIN_PASSWORD_LENGTH} chars): ")
                if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
                    print(f"Error: Password must be at least {MIN_ADMIN_PASSWORD_LENGTH} characters long.")
                    continue
                confirm = getpass.getpass("Confirm new admin password: ")
                if password != confirm:
                    print("Error: Passwords do not match. Please try again.")
                    continue
                break

        try:
            rotate_admin_password(username, password)
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
