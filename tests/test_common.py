import pytest
from utils.common import get_sql_connection

def test_sql_connection():
    conn = get_sql_connection()
    assert conn is not None