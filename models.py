from db import get_connection
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------- USERS ----------------

def create_user(username, password, mobile):

    conn = get_connection()
    cur = conn.cursor()

    hashed_password = generate_password_hash(password)

    cur.execute("""
    INSERT INTO users (username, password, mobile)
    VALUES (?, ?, ?)
    """, (username, hashed_password, mobile))

    conn.commit()
    conn.close()


def get_user(username, password):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT * FROM users WHERE username=?
    """, (username,))

    user = cur.fetchone()

    conn.close()

    if user and check_password_hash(user["password"], password):
        return user

    return None


def get_all_users():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users")

    users = cur.fetchall()

    conn.close()

    return users


# ---------------- ADMIN ----------------

def get_admin(username, password):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT * FROM admin
    WHERE username=? AND password=?
    """, (username, password))

    admin = cur.fetchone()

    conn.close()

    return admin


# ---------------- SLOT LOGIC ----------------

def get_available_slots(start=None, end=None):

    conn = get_connection()
    cur = conn.cursor()

    if not start or not end:

        cur.execute("""
        SELECT * FROM slots
        WHERE is_available=1
        """)

        slots = cur.fetchall()

        conn.close()

        return slots

    cur.execute("""
    SELECT slot_number FROM bookings
    WHERE NOT (? >= duration OR ? <= entry_time)
    """, (start, end))

    booked = [row["slot_number"] for row in cur.fetchall()]

    cur.execute("""
    SELECT * FROM slots
    WHERE is_available=1
    """)

    all_slots = cur.fetchall()

    available = [
        s for s in all_slots
        if s["slot_number"] not in booked
    ]

    conn.close()

    return available


def is_slot_available(slot, start, end):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT * FROM bookings
    WHERE slot_number = ?
    AND NOT (? >= duration OR ? <= entry_time)
    """, (slot, start, end))

    conflict = cur.fetchone()

    conn.close()

    return conflict is None


# ---------------- PRICE ----------------

def calculate_price(start, end):

    start = datetime.fromisoformat(start)
    end = datetime.fromisoformat(end)

    hours = (end - start).total_seconds() / 3600

    rate = 100 if hours < 0.75 else 50

    return round(hours * rate, 2)


# ---------------- BOOKINGS ----------------

def create_booking(
        user_id,
        vehicle,
        mobile,
        slot,
        start,
        end,
        payment_id,
        amount
):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO bookings
    (
        user_id,
        vehicle_number,
        mobile,
        slot_number,
        entry_time,
        duration,
        payment_id,
        amount
    )

    VALUES (?, ?, ?, ?, ?, ?, ?, ?)

    """, (
        user_id,
        vehicle,
        mobile,
        slot,
        start,
        end,
        payment_id,
        amount
    ))

    cur.execute("""
    UPDATE slots
    SET is_available=0
    WHERE slot_number=?
    """, (slot,))

    conn.commit()
    conn.close()


def get_user_bookings(user_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT * FROM bookings
    WHERE user_id=?
    """, (user_id,))

    data = cur.fetchall()

    conn.close()

    return data


def get_all_bookings():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT * FROM bookings
    """)

    data = cur.fetchall()

    conn.close()

    return data


def delete_booking(id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT slot_number FROM bookings
    WHERE id=?
    """, (id,))

    slot = cur.fetchone()["slot_number"]

    cur.execute("""
    DELETE FROM bookings
    WHERE id=?
    """, (id,))

    cur.execute("""
    UPDATE slots
    SET is_available=1
    WHERE slot_number=?
    """, (slot,))

    conn.commit()
    conn.close()


def exit_vehicle(id):
    delete_booking(id)


# ---------------- DASHBOARD ----------------

def get_total_bookings():
    return len(get_all_bookings())


def get_occupied_slots():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT COUNT(*) as c
    FROM slots
    WHERE is_available=0
    """)

    val = cur.fetchone()["c"]

    conn.close()

    return val


def get_available_slots_count():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT COUNT(*) as c
    FROM slots
    WHERE is_available=1
    """)

    val = cur.fetchone()["c"]

    conn.close()

    return val


# ---------------- SEARCH ----------------

def search_vehicle(vehicle):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT * FROM bookings
    WHERE vehicle_number LIKE ?
    """, ('%' + vehicle + '%',))

    data = cur.fetchall()

    conn.close()

    return data


# ---------------- BI ANALYTICS ----------------

def get_total_revenue():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT amount FROM bookings
    """)

    rows = cur.fetchall()

    conn.close()

    total = sum([r["amount"] for r in rows])

    return round(total, 2)


def get_peak_hour():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT entry_time FROM bookings
    """)

    rows = cur.fetchall()

    conn.close()

    hours = [0] * 24

    for r in rows:

        h = datetime.fromisoformat(
            r["entry_time"]
        ).hour

        hours[h] += 1

    return hours.index(max(hours)) if max(hours) > 0 else 0


def get_daily_bookings():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT entry_time FROM bookings
    """)

    rows = cur.fetchall()

    conn.close()

    data = {}

    for r in rows:

        d = str(
            datetime.fromisoformat(
                r["entry_time"]
            ).date()
        )

        data[d] = data.get(d, 0) + 1

    return list(data.keys()), list(data.values())


# ---------------- INVOICE ----------------

def save_invoice(payment_id, amount, user_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS invoices(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_id TEXT,
        amount REAL,
        user_id INTEGER
    )
    """)

    cur.execute("""
    INSERT INTO invoices(payment_id, amount, user_id)
    VALUES (?, ?, ?)
    """, (payment_id, amount, user_id))

    conn.commit()
    conn.close()


# ---------------- REFUND ----------------

def save_refund(payment_id, amount):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS refunds(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_id TEXT,
        amount REAL
    )
    """)

    cur.execute("""
    INSERT INTO refunds(payment_id, amount)
    VALUES (?, ?)
    """, (payment_id, amount))

    conn.commit()
    conn.close()