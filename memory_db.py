import sqlite3
from embedding import get_embedding



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


if __name__ == "__main__" :
    setup_db()
    