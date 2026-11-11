import os

# Process-level test isolation:
# Strip ambient host DATABASE_URL so test configuration is isolated from host environment.
# Note: os.environ modification is strictly process-local and preserves Windows User/Machine environment variables.
os.environ.pop("DATABASE_URL", None)

import pytest
from app import create_app
from app.models.db import db
from app.database import init_db


@pytest.fixture
def app():
    """Create application configured for testing."""
    test_app = create_app("testing")
    with test_app.app_context():
        init_db(drop_all=True)
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client for HTTP requests."""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Provide clean database session for each test."""
    return db.session
