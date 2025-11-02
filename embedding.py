from sentence_transformers import SentenceTransformer
import json

embedder = SentenceTransformer("all-MiniLM-L6-v2")

def get_embedding(text :str) :
    """
       Return embedding vector for given text
    """

    emb = embedder.encode(text, convert_to_numpy=True).tolist()
    return json.dumps(emb)