import sqlite3
from embedding import get_embedding
import numpy as np
import json


def cosine_sim(a,b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

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
     auto_link_memory(memory_id, np.array(json.loads(embedding)), db_path=db_path)
     return memory_id

def auto_link_memory(new_id, new_emb, db_path="memory.db", threshold=0.85):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id, embedding FROM memories WHERE id != ?", (new_id,))
    for row in c.fetchall():
        old_id, old_emb_str = row
        old_emb = np.array(json.loads(old_emb_str))
        score = cosine_sim(new_emb, old_emb)
        if score >= threshold:
            c.execute("""
            
              INSERT OR IGNORE INTO memory_links (source_id,target_id, similarity) VALUES (?,?,?)
""", (new_id, old_id, score))
            
            print(f"Linked to #{old_id} (score: {score:.2f})")
   
    conn.commit()
    conn.close()



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


def setup_links_table(db_path="memory.db"):
    conn=sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""

      CREATE TABLE IF NOT EXISTS memory_links(
              id INTEGER PRIMARY KEY AUTOINCREMENT, 
              source_id INTEGER,
              target_id INTEGER,
              similarity REAL, 
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              UNIQUE(source_id, target_id))

""")
    conn.commit()
    conn.close()


if __name__ == "__main__" :
    setup_db()
    setup_links_table()
    