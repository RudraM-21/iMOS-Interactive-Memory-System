import sqlite3
from .embedding import get_embedding
import numpy as np
import json
import hashlib
import re


def extract_actions_from_text(text):
    """
    Extract action items from text with flexible pattern matching.
    Handles various formats like:
    - TODO: Do something
    - TODO : Do something (with space before colon)
    - Action - Do something
    - TASK Do something (no punctuation)
    - - [ ] Do something (markdown checkbox)
    - * [ ] Do something (markdown checkbox)
    """
    actions = []
    
    # Pattern 1: Action keywords with optional punctuation and flexible spacing
    # Matches: TODO:, TODO :, TODO-, TODO , etc.
    keyword_pattern = re.compile(
        r'^\s*(?:TODO|Action|Next|Follow\s*Up|Task)\s*[:\-]?\s*(.+)$', 
        re.IGNORECASE | re.MULTILINE
    )
    
    # Pattern 2: Markdown-style checkboxes
    # Matches: - [ ] something, * [ ] something
    checkbox_pattern = re.compile(
        r'^\s*[-*]\s*\[\s*\]\s*(.+)$', 
        re.MULTILINE
    )
    
    # Extract from keyword patterns
    for match in keyword_pattern.finditer(text):
        action_text = match.group(1).strip()
        if action_text:  # Only add non-empty actions
            actions.append(action_text)
    
    # Extract from checkbox patterns
    for match in checkbox_pattern.finditer(text):
        action_text = match.group(1).strip()
        if action_text:  # Only add non-empty actions
            actions.append(action_text)
    
    return actions

def compute_text_hash(text):
    return hashlib.sha256(text.replace('\n', '').strip().encode('utf-8')).hexdigest()


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
              source TEXT DEFAULT 'manual',
              text_hash TEXT UNIQUE
              )    

""")
    
    # Setup actions table
    c.execute("""
        CREATE TABLE IF NOT EXISTS actions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_text TEXT NOT NULL,
            source TEXT DEFAULT 'manual',
            memory_id INTEGER,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(memory_id) REFERENCES memories(id)
        )
    """)
    
    conn.commit()
    conn.close()


def add_memory(text, source="manual", db_path="memory.db", auto_link=False) :
     
     embedding = get_embedding(text)
     text_hash = compute_text_hash(text)
     conn = sqlite3.connect(db_path)
     c = conn.cursor()

     c.execute(
     "SELECT id FROM memories WHERE text_hash = ?",(text_hash,))

     if c.fetchone():
        conn.close()
        print(f"Skipped duplicate memory(hash : {text_hash[:8]})")
        return None
        
     c.execute("INSERT INTO memories (text, embedding, source, text_hash) VALUES (?, ?, ?, ?)", (text, embedding, source, text_hash))
     conn.commit()
     memory_id = c.lastrowid
     conn.close()

     actions = extract_actions_from_text(text)
     if actions:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        for action in actions:
            c.execute(
                "INSERT INTO actions (action_text, source, memory_id) VALUES (?, ?, ?)",
                (action, source, memory_id)
            )
        conn.commit()
        conn.close()
     
     if auto_link:
         try:
             auto_link_memory(memory_id, np.array(json.loads(embedding)), db_path=db_path)
         except Exception as e:
             print(f"Warning: Could not auto-link memory {memory_id}: {e}")
     
     return memory_id

def auto_link_memory(new_id, new_emb, db_path="memory.db", threshold=0.85):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id, embedding FROM memories WHERE id <> ?", (new_id,))
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
    """Get all memories with embeddings. Use with caution for large databases."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id, text, embedding, source FROM memories")
    rows = c.fetchall()
    conn.close()
    return [{
        "id" : row[0],
        "text" : row[1],
        "embedding" : np.array(json.loads(row[2])),
        "source": row[3]}
        for row in rows
    ]

def search_memories_fast(query_embedding, top_k=5, db_path="memory.db"):
    """
    Fast memory search using vectorized operations.
    Returns top_k most similar memories without loading all into memory.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Get all embeddings and IDs (still need to load for similarity, but more efficient)
    c.execute("SELECT id, embedding, text, source FROM memories")
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        return []
    
    # Vectorized similarity computation
    ids = []
    embeddings = []
    texts = []
    sources = []
    
    for row in rows:
        ids.append(row[0])
        embeddings.append(np.array(json.loads(row[1])))
        texts.append(row[2])
        sources.append(row[3])
    
    # Stack embeddings for vectorized operations
    embeddings_matrix = np.stack(embeddings)
    
    # Vectorized cosine similarity
    query_norm = np.linalg.norm(query_embedding)
    embedding_norms = np.linalg.norm(embeddings_matrix, axis=1)
    similarities = np.dot(embeddings_matrix, query_embedding) / (embedding_norms * query_norm)
    
    # Get top_k indices
    top_indices = np.argpartition(similarities, -top_k)[-top_k:]
    top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]
    
    results = []
    for idx in top_indices:
        results.append({
            "id": ids[idx],
            "text": texts[idx],
            "source": sources[idx],
            "embedding": embeddings[idx],
            "similarity": similarities[idx]
        })
    
    return results


def get_linked_memories(memory_id, db_path="memory.db", min_similarity=0.85):
    """
    Get all memories linked to a given memory ID.
    Returns list of memory dicts with similarity scores.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Get both directions of links (source->target and target->source)
    c.execute("""
        SELECT target_id, similarity FROM memory_links 
        WHERE source_id = ? AND similarity >= ?
        UNION
        SELECT source_id, similarity FROM memory_links 
        WHERE target_id = ? AND similarity >= ?
    """, (memory_id, min_similarity, memory_id, min_similarity))
    
    linked_ids = c.fetchall()
    
    if not linked_ids:
        conn.close()
        return []
    
    # Fetch full memory data for linked IDs
    linked_memories = []
    for lid, sim in linked_ids:
        c.execute("SELECT id, text, embedding, source FROM memories WHERE id = ?", (lid,))
        row = c.fetchone()
        if row:
            linked_memories.append({
                "id": row[0],
                "text": row[1],
                "embedding": np.array(json.loads(row[2])),
                "source": row[3],
                "link_similarity": sim
            })
    
    conn.close()
    return linked_memories


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