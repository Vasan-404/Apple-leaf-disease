import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "apple_leaf.db"

username = "admin"
password = "admin123"

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
""")

cur.execute("SELECT * FROM admin WHERE username = ?", (username,))
existing_admin = cur.fetchone()

if existing_admin is None:
    cur.execute(
        "INSERT INTO admin (username, password) VALUES (?, ?)",
        (username, generate_password_hash(password))
    )
    conn.commit()
    print("Admin created successfully.")
else:
    print("Admin already exists.")

conn.close()