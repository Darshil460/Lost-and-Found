import sqlite3


DATABASE = "lostandfound.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    # Makes SQLite enforce foreign-key relationships
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def init_db():

    connection = get_connection()
    cursor = connection.cursor()


    # ========================================
    # USERS TABLE
    # ========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            registration_id TEXT PRIMARY KEY
        )
    """)


    # ========================================
    # ITEMS TABLE
    # ========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            finder_id TEXT,
            location_type TEXT NOT NULL,
            location TEXT NOT NULL,
            item TEXT NOT NULL,
            description TEXT NOT NULL,
            picture TEXT,
            status TEXT NOT NULL DEFAULT 'unclaimed',

            FOREIGN KEY (finder_id)
                REFERENCES users(registration_id)
        )
    """)


    # ========================================
    # MIGRATE OLD ITEMS TABLE
    # ========================================

    # Check whether finder_id already exists

    cursor.execute("""
        PRAGMA table_info(items)
    """)

    item_columns = [
        column["name"]
        for column in cursor.fetchall()
    ]


    # If this is our old database, add finder_id

    if "finder_id" not in item_columns:

        cursor.execute("""
            ALTER TABLE items
            ADD COLUMN finder_id TEXT
        """)


    # ========================================
    # CLAIMS TABLE
    # ========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            looker_id TEXT,
            status TEXT NOT NULL DEFAULT 'pending',

            FOREIGN KEY (item_id)
                REFERENCES items(id),

            FOREIGN KEY (looker_id)
                REFERENCES users(registration_id)
        )
    """)


    # ========================================
    # MIGRATE OLD CLAIMS TABLE
    # ========================================

    cursor.execute("""
        PRAGMA table_info(claims)
    """)

    claim_columns = [
        column["name"]
        for column in cursor.fetchall()
    ]


    # If this is our old database, add looker_id

    if "looker_id" not in claim_columns:

        cursor.execute("""
            ALTER TABLE claims
            ADD COLUMN looker_id TEXT
        """)


    connection.commit()
    connection.close()