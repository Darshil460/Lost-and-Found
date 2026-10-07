import sqlite3


DATABASE = "lostandfound.db"




def get_connection():
    connection = sqlite3.connect(DATABASE, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
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

    cursor.execute("""
        PRAGMA table_info(items)
    """)

    item_columns = [
        column["name"]
        for column in cursor.fetchall()
    ]


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


    if "looker_id" not in claim_columns:

        cursor.execute("""
            ALTER TABLE claims
            ADD COLUMN looker_id TEXT
        """)


    # ========================================
    # VERIFICATION QUESTIONS TABLE
    # ========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verification_questions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            item_id INTEGER NOT NULL,

            question TEXT NOT NULL,

            answer TEXT NOT NULL,

            FOREIGN KEY (item_id)
                REFERENCES items(id)
                ON DELETE CASCADE
        )
        """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS claim_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id INTEGER NOT NULL,
            sender_id TEXT NOT NULL,
            sender_role TEXT NOT NULL
                CHECK (sender_role IN ('finder', 'looker')),
            body TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (claim_id)
                REFERENCES claims(id)
                ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_claim_messages_claim_id_id
        ON claim_messages (claim_id, id)
    """)

    connection.commit()

    connection.close()