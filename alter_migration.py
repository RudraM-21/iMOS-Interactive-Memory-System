import sqlite3

db_path = "memory.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Add the new column if it doesn't exist already
try:
    c.execute("ALTER TABLE memories ADD COLUMN text_hash TEXT")
    print("✅ Added text_hash column to memories")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("Column already exists, nothing to do.")
    else:
        raise
conn.commit()
conn.close()
