import sqlite3

DB_NAME = "parking.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # ✅ Enable WAL mode (VERY IMPORTANT)
    cur.execute("PRAGMA journal_mode=WAL;")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        mobile TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slot_number INTEGER UNIQUE,
        is_available INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        vehicle_number TEXT,
        mobile TEXT,
        slot_number INTEGER,
        entry_time TEXT,
        duration TEXT,
        payment_id TEXT,
        amount REAL
    )
    """)

    conn.commit()

    # Default admin
    cur.execute("SELECT * FROM admin WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO admin (username, password) VALUES ('admin','admin123')")

    conn.commit()
    conn.close()

def create_slots(n=10):
    conn = get_connection()
    cur = conn.cursor()

    for i in range(1, n+1):
        cur.execute("INSERT OR IGNORE INTO slots (slot_number) VALUES (?)", (i,))

    conn.commit()
    conn.close()