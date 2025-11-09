# import sqlite3

# db_path = "memory.db"
# conn = sqlite3.connect(db_path)
# c = conn.cursor()

# # Add the new column if it doesn't exist already
# try:
#     c.execute("ALTER TABLE memories ADD COLUMN text_hash TEXT")
#     print("✅ Added text_hash column to memories")
# except sqlite3.OperationalError as e:
#     if "duplicate column name" in str(e):
#         print("Column already exists, nothing to do.")
#     else:
#         raise
# conn.commit()
# conn.close()



def setup_actions_table(db_path="memory.db"):
    import sqlite3
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action_text TEXT NOT NULL,
        source TEXT,
        memory_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'open'
    )
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    setup_actions_table()