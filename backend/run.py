import os
from app import create_app
from app.database import init_db

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        init_db()
    port = int(os.environ.get("PORT", 5000))
    # Derive debug mode from configuration; strictly disable in production
    debug_mode = bool(app.config.get("DEBUG", False))
    if app.config.get("ENV") == "production" or os.environ.get("FLASK_ENV", "").lower() == "production":
        debug_mode = False
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
