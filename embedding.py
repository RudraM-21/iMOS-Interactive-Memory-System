from sentence_transformers import SentenceTransformer
import json

# Global embedder instance (lazy loaded)
_embedder = None

def get_embedder():
    """Get cached sentence transformer instance (loads only once)"""
    global _embedder
    if _embedder is None:
        print("Loading embedding model (one-time setup)...")
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder

def get_embedding(text: str) -> str:
    """
    Return embedding vector for given text as JSON string.
    Uses cached model instance for speed.
    """
    embedder = get_embedder()
    emb = embedder.encode(text, convert_to_numpy=True).tolist()
    return json.dumps(emb)