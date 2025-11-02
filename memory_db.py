import sqlite3
from embedding import get_embedding
import numpy as np
import json


def setup_db(db_path="memory.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
         
      CREATE TABLE IF NOT EXISTS memories(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              text TEXT NOT NULL,
              embedding TEXT NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              source TEXT DEFAULT 'manual'
              )    

""")
    
    conn.commit()
    conn.close()


def add_memory(text, source="manual", db_path="memory.db") :
     
     embedding = get_embedding(text)
     conn = sqlite3.connect(db_path)
     c = conn.cursor()
        
     c.execute("INSERT INTO memories (text, embedding, source) VALUES (?, ?, ?)", (text, embedding, source))
     conn.commit()
     memory_id = c.lastrowid
     conn.close()
     return memory_id


def get_all_memories(db_path="memory.db"):

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id, text, embedding FROM memories")
    rows = c.fetchall()
    conn.close()
    return [{
        "id" : row[0],
        "text" : row[1],
        "embedding" : np.array(json.loads(row[2]))}
        for row in rows
    ]




if __name__ == "__main__" :
    setup_db()
    