
from app.db.database import check_database_connection


def test_postgresql_connection():
    assert check_database_connection() is True
