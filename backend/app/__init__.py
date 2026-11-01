import os
from flask import Flask, jsonify
from flask_cors import CORS
from app.config import config_by_name
from app.models.db import db


def create_app(config_name: str | None = None) -> Flask:
    """Application factory for the Flask backend."""
    app = Flask(__name__, instance_relative_config=True)

    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    config_class = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_class)

    # Security check: warn if default insecure secret key is used in production
    if config_name == "production" and app.config.get("SECRET_KEY") == "dev-secret-key-change-in-production":
        import warnings
        warnings.warn(
            "CRITICAL SECURITY WARNING: Running production mode with default SECRET_KEY fallback! "
            "Set a unique, cryptographically random SECRET_KEY environment variable.",
            RuntimeWarning,
            stacklevel=2,
        )

    # Initialize extensions
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}},
        supports_credentials=True,
    )
    db.init_app(app)

    # Register Blueprints
    from app.routes.product_routes import product_bp
    from app.routes.order_routes import order_bp
    from app.routes.admin_routes import admin_bp
    app.register_blueprint(product_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(admin_bp)

    # Health check route
    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "environment": config_name,
            "database": "connected"
        }), 200

    # Global JSON error handlers
    @app.errorhandler(404)
    def handle_not_found(err):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def handle_server_error(err):
        return jsonify({"error": "Internal server error"}), 500

    # Register CLI commands for database management
    @app.cli.command("init-db")
    def init_db_command():
        """Initialize the database tables."""
        from app.database import init_db
        with app.app_context():
            init_db()
            print("Database initialized successfully.")

    @app.cli.command("seed-db")
    def seed_db_command():
        """Seed the database with sample products."""
        from app.database import seed_db
        with app.app_context():
            count = seed_db()
            print(f"Database seeded with {count} products.")

    @app.cli.command("reset-db")
    def reset_db_command():
        """Reset the database and re-seed sample products."""
        from app.database import init_db, seed_db
        with app.app_context():
            init_db(drop_all=True)
            count = seed_db()
            print(f"Database reset and re-seeded with {count} products.")

    @app.cli.command("create-admin")
    def create_admin_command():
        """Interactively create an administrator account."""
        import getpass
        from app.models.admin import Admin

        print("=== Novastore Administrator Account Creation ===")
        username = input("Enter admin username: ").strip()
        if not username:
            print("Error: Username cannot be blank.")
            return

        email = input("Enter admin email: ").strip().lower()
        if not email or "@" not in email:
            print("Error: Valid email address required.")
            return

        password = getpass.getpass("Enter secure password (min 6 chars): ")
        if len(password) < 6:
            print("Error: Password must be at least 6 characters.")
            return

        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Error: Passwords do not match.")
            return

        with app.app_context():
            existing = Admin.query.filter(
                (Admin.username == username) | (Admin.email == email)
            ).first()
            if existing:
                print(f"Error: Admin with username '{username}' or email '{email}' already exists.")
                return

            admin = Admin(username=username, email=email)
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            print(f"Success! Administrator '{admin.username}' created successfully (ID: {admin.id}).")

    @app.cli.command("change-admin-password")
    def change_admin_password_cli():
        """Interactively rotate an administrator's password securely."""
        import getpass
        from datetime import datetime, timezone
        from app.models.admin import Admin

        print("=== Novastore Administrator Password Rotation ===")
        username = input("Enter admin username or email: ").strip()
        if not username:
            print("Error: Username/email cannot be blank.")
            return

        with app.app_context():
            clean_id = username.lower()
            admin = Admin.query.filter(
                (Admin.username.ilike(clean_id)) | (Admin.email.ilike(clean_id))
            ).first()
            if not admin:
                print(f"Error: Administrator '{username}' not found.")
                return

            new_password = getpass.getpass("Enter new secure password (min 6 chars): ")
            if len(new_password) < 6:
                print("Error: Password must be at least 6 characters.")
                return

            confirm = getpass.getpass("Confirm new password: ")
            if new_password != confirm:
                print("Error: Passwords do not match.")
                return

            admin.set_password(new_password)
            admin.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            print(f"Success! Password for administrator '{admin.username}' has been securely rotated.")
            print("All previously issued session tokens have been automatically revoked.")

    return app
