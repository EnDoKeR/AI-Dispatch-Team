import sqlite3
from pathlib import Path


SQLITE_DB_FILE = Path("data/dispatch_memory.db")


def connect_db(db_path=SQLITE_DB_FILE):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    return connection
