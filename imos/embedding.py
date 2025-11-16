from sentence_transformers import SentenceTransformer
import json
import os
from pathlib import Path

# Global embedder instance (lazy loaded)
_embedder = None

def get_model_cache_path():
    """Get the path for caching the model locally"""
    home_dir = Path.home()
    cache_dir = home_dir / ".imos" / "model_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

def get_embedder():
    """Get cached sentence transformer instance (loads only once per session)"""
    global _embedder
    if _embedder is None:
        cache_path = get_model_cache_path()
        
        # Try to load from cache first
        if (cache_path / "config.json").exists():
            # Model exists in cache - load silently and quickly
            _embedder = SentenceTransformer(str(cache_path))
        else:
            # First time - download and cache
            print("🔄 Setting up IMOS for first use (downloading model)...")
            print("   This only happens once and makes future queries instant!")
            _embedder = SentenceTransformer("all-MiniLM-L6-v2")
            # Save to cache for future use
            _embedder.save(str(cache_path))
            print("✅ Setup complete! Future queries will be instant.")
    return _embedder

def get_embedding(text: str) -> str:
    """
    Return embedding vector for given text as JSON string.
    Uses cached model instance for speed.
    """
    embedder = get_embedder()
    emb = embedder.encode(text, convert_to_numpy=True).tolist()
    return json.dumps(emb)