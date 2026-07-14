import os

# Fall back to SQLite when DATABASE_URL is not set (local dev without Docker).
# pytest-django picks up DJANGO_SETTINGS_MODULE from pytest.ini.
os.environ.setdefault("DATABASE_URL", "sqlite:///test_db.sqlite3")
