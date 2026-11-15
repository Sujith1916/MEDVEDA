import sqlite3

DATABASE_NAME = "medical_records.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS medical_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_reference TEXT NOT NULL,
            medical_system TEXT NOT NULL,
            record_type TEXT NOT NULL,
            condition_terms TEXT NOT NULL,
            medicines TEXT NOT NULL,
            notes TEXT,
            comments TEXT
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users (username COLLATE NOCASE)")

    # Ensure 'comments' column exists if upgrading an existing database
    cursor = connection.cursor()
    cursor.execute("PRAGMA table_info(medical_records)")
    columns = [row[1] for row in cursor.fetchall()]
    if "comments" not in columns:
        cursor.execute("ALTER TABLE medical_records ADD COLUMN comments TEXT")

    connection.commit()
    connection.close()
