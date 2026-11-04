import os
from flask import Flask, jsonify
from flask_cors import CORS
from app.config import config_by_name, INSECURE_SECRET_KEYS, MIN_PRODUCTION_SECRET_KEY_LENGTH
from app.models.db import db

MIN_ADMIN_PASSWORD_LENGTH = 8


def parse_cors_origins(origins_val):
    """Normalize CORS origins string or sequence into a list of cleaned origin strings."""
    if origins_val is None:
        return []
    if isinstance(origins_val, (list, tuple, set)):
        return [str(o).strip() for o in origins_val if str(o).strip()]
    if isinstance(origins_val, str):
        return [o.strip() for o in origins_val.split(",") if o.strip()]
    return [str(origins_val).strip()]


def create_app(config_name: str | None = None) -> Flask:
    """Application factory for the Flask backend."""
    app = Flask(__name__, instance_relative_config=True)

    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development").lower()

    config_class = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_class)

    is_production = (
        config_name == "production"
        or app.config.get("ENV") == "production"
    )

    if is_production:
        # In production, ensure live environment variables take precedence
        app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
        app.config["CORS_ORIGINS"] = os.environ.get("CORS_ORIGINS")

        # TASK 1: Production SECRET_KEY enforcement
        secret_key = app.config.get("SECRET_KEY")
        if not secret_key or not str(secret_key).strip():
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: SECRET_KEY is not configured for production. "
                "Application startup aborted. Set a unique, cryptographically random SECRET_KEY environment variable."
            )
        if str(secret_key).strip() in INSECURE_SECRET_KEYS:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: Insecure or default development SECRET_KEY cannot be used in production. "
                "Application startup aborted. Configure a cryptographically secure random secret key."
            )
        if len(str(secret_key).strip()) < MIN_PRODUCTION_SECRET_KEY_LENGTH:
            raise RuntimeError(
                f"CRITICAL SECURITY ERROR: Production SECRET_KEY must be at least "
                f"{MIN_PRODUCTION_SECRET_KEY_LENGTH} characters long. Application startup aborted."
            )

        # TASK 2: CORS hardening in production
        cors_raw = app.config.get("CORS_ORIGINS")
        parsed_origins = parse_cors_origins(cors_raw)
        if not parsed_origins:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: CORS_ORIGINS is not configured for production. "
                "Application startup aborted. Explicit allowed origins must be specified."
            )
        if any(origin == "*" for origin in parsed_origins):
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: Wildcard CORS origin ('*') is strictly forbidden in production mode. "
                "Application startup aborted. Specify explicit allowed origin(s) in CORS_ORIGINS."
            )
        cors_origins = parsed_origins
    else:
        if "SECRET_KEY" in os.environ and config_name != "testing":
            app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
        if "CORS_ORIGINS" in os.environ:
            app.config["CORS_ORIGINS"] = os.environ.get("CORS_ORIGINS")

        cors_raw = app.config.get("CORS_ORIGINS", "*")
        if cors_raw == "*":
            cors_origins = "*"
        else:
            cors_origins = parse_cors_origins(cors_raw)

    # Initialize extensions
    CORS(
        app,
        resources={r"/api/*": {"origins": cors_origins}},
        supports_credentials=True,
    )
    db.init_app(app)

    # Configure trusted reverse proxy support if explicitly configured
    trusted_proxies = app.config.get("TRUSTED_PROXIES_COUNT", 0)
    if isinstance(trusted_proxies, int) and trusted_proxies > 0:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=trusted_proxies,
            x_proto=trusted_proxies,
            x_host=trusted_proxies,
            x_port=trusted_proxies,
            x_prefix=trusted_proxies,
        )

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

        password = getpass.getpass(f"Enter secure password (min {MIN_ADMIN_PASSWORD_LENGTH} chars): ")
        if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
            print(f"Error: Password must be at least {MIN_ADMIN_PASSWORD_LENGTH} characters.")
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

            new_password = getpass.getpass(f"Enter new secure password (min {MIN_ADMIN_PASSWORD_LENGTH} chars): ")
            if len(new_password) < MIN_ADMIN_PASSWORD_LENGTH:
                print(f"Error: Password must be at least {MIN_ADMIN_PASSWORD_LENGTH} characters.")
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
