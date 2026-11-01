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
    app.register_blueprint(product_bp)
    app.register_blueprint(order_bp)

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

    return app
