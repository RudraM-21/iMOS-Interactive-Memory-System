import sqlite3
import typer
from memory_db import setup_db, add_memory, get_all_memories
import numpy as np
from embedding import get_embedding
import json
import os
from utils import extract_text_from_file

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


@app.command()
def links(id: int):
    """Show linked memories for a memory ID"""
    conn = sqlite3.connect("memory.db")
    c = conn.cursor()
    c.execute("SELECT target_id, similarity FROM memory_links WHERE source_id=?", (id,))
    linked = c.fetchall()
    conn.close()
    for tgt, sim in linked:
        typer.echo(f"Linked to #{tgt} (score: {sim:.2f})")


@app.command()
def list():
    """List all stored memories (ID, text, summary)."""
    memories = get_all_memories()
    for memory in memories:
        snippet = memory["text"][:60].replace('\n',' ')
        typer.echo(f"[{memory['id']:>3}] {snippet}" + ("..." if len(memory["text"]) > 60 else ""))


@app.command()
def addfile(path:str):
    """Import a file into IMOS memory."""
    
    try:
        text = extract_text_from_file(path)
        memory_id = add_memory(text, source=path)
        typer.echo(f"Imported '{path}' as memory #{memory_id}")
    except Exception as e:
        typer.secho(f"Error importing file: {e}", fg=typer.colors.RED)


@app.command()
def import_folder(path:str):
     
    """
    Import all .txt, .pdf, .docx files in a directory (recursively) into IMOS memory.
    Usage: imos.py import-folder /path/to/memories
    """

    imported = 0
    failed =0

    for root, dirs, files in os.walk(path):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in [".txt",".pdf",".docx"]:
                fpath = os.path.join(root, fname)
                try:
                    text = extract_text_from_file(fpath)
                    add_memory(text, source=fpath)
                    imported += 1
                    typer.echo(f"Imported: {fpath}")
                except Exception as e:
                    failed += 1
                    typer.secho(f"Error with {fpath} : {e}", fg=typer.colors.RED)
    
    typer.echo(f"\n Imported {imported} files from {path} ({failed} failed)")



if __name__ == "__main__" :
    setup_db()
    app()