import typer
from memory_db import setup_db, add_memory, get_all_memories
import numpy as np
from embedding import get_embedding
import json


def cosine_sim(a,b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


app = typer.Typer()

@app.callback()
def main():
    """
    Memory management CLI
    """
    pass

@app.command()
def add(text:str, source:str="manual"):
    """Add a new memory"""
    memory_id = add_memory(text=text, source=source)
    typer.echo(f"Added memory #{memory_id}")


@app.command()
def ask(query: str, top_k: int=3):
    """Ask IMOS a question, returns the most relevant memories."""
    
    query_emb = np.array(json.loads(get_embedding(query)))
    memories = get_all_memories()
    results =[]

    for memory in memories :
        score = cosine_sim(query_emb, memory["embedding"])
        results.append((score, memory['id'], memory['text']))
    results.sort(reverse=True)

    typer.echo(f"Found:")
    for rank, (score, memory_id, text) in enumerate(results[:top_k], 1):
        typer.secho(f"{rank}. [{memory_id}] {text}", fg=typer.colors.BRIGHT_GREEN)
        typer.echo(f"  (Score: {score:.3f})")


if __name__ == "__main__" :
    setup_db()
    app()