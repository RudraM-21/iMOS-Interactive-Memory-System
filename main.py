import sqlite3
import typer
from memory_db import setup_db, setup_links_table, add_memory, get_all_memories
import numpy as np
from embedding import get_embedding
import json
import os
from utils import extract_text_from_file
import requests
from dotenv import load_dotenv

load_dotenv()



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
    search_results =[]

    for memory in memories :
        score = cosine_sim(query_emb, memory["embedding"])
        search_results.append((score, memory))
    search_results.sort(reverse=True, key=lambda x:x[0])
    top_memories = [item[1] for item in search_results[:top_k]]

    def build_prompt(query, memory_list):
        prompt = (
            f"You are IMOS, a thoughtful local memory assistant.\n"
            f"A user asked: '{query}'\n\n"
            f"Here are notes and ideas from their personal library.\n"
        )
        for memory in memory_list:
            source = memory.get("source","manual")
            txt = memory["text"].replace("\n", " ")
            prompt += f"- [{source}] : {txt}\n"
        prompt += (
            "\nPlease answer conversationally (like a friend or coach), weaving key insights."
            "Reference their notes (use file names if useful), and avoid robotic tone."
        )
        return prompt
    
    full_prompt = build_prompt(query, top_memories)

    def get_llm_response(prompt, groq_api_key, model="llama-3.1-8b-instant"):
        api_url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }
        payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are IMOS, a thoughtful, local memory assistant. Answer like a friend, referencing the user's memories as needed."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 512,
        "temperature": 0.6
    }
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']

    groq_api_key = os.getenv("GROQ_API_KEY")
    answer = get_llm_response(full_prompt, groq_api_key)
    typer.secho("\nIMOS>", fg=typer.colors.CYAN)
    typer.echo(answer)


@app.command()
def chat(top_k: int = 3):
    """
    Start IMOS in chat mode. You can ask multiple questions. Type 'exit' or 'quit' to stop.
    Now supports multi-turn session context for richer, conversational answers.
    """

    groq_api_key = os.getenv("GROQ_API_KEY")
    print("IMOS Chat Mode. Type your question; type 'exit' to leave.")

    # Load all memories and embeddings once for session speed
    memories = get_all_memories()
    session_history = [
        {"role": "system", "content": "You are IMOS, a thoughtful, local memory assistant. Answer like a friend, always referencing the user's memories as needed."}
    ]

    def build_memory_context(query, memory_list):
        prompt = (
            f"Here are notes, ideas, and files relevant to the user's current question:\n"
        )
        for mem in memory_list:
            source = mem.get("source", "manual")
            txt = mem["text"].replace("\n", " ")
            prompt += f"- [{source}]: {txt}\n"
        prompt += (
            "\nPlease answer conversationally, like a friend or coach, weaving relevant insights and facts. "
            "Cite file/source names when you reference a specific memory."
        )
        return prompt

    def get_llm_response(messages, groq_api_key, model="llama-3.1-8b-instant"):
        api_url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.6
        }
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']

    while True:
        query = input("imos> ").strip()
        if query.lower() in ["exit", "quit"]:
            print("Exiting IMOS Chat. All recent conversations are in your log (if enabled).")
            break

        query_emb = np.array(json.loads(get_embedding(query)))
        search_results = [
            (np.dot(query_emb, memory["embedding"]) / (np.linalg.norm(query_emb) * np.linalg.norm(memory["embedding"])), memory)
            for memory in memories
        ]
        search_results.sort(reverse=True, key=lambda x: x[0])
        top_memories = [item[1] for item in search_results[:top_k]]

        # Build memory context (relevant memories)
        memory_context = build_memory_context(query, top_memories)

        # Add this turn to session: user question with memory context
        session_history.append({
            "role": "user",
            "content": f"{query}\n\n{memory_context}"
        })

        # Get LLM answer from Groq, given all session context so far
        answer = get_llm_response(session_history, groq_api_key)

        # Print the answer (conversational, context-aware)
        print("\nIMOS>", answer)
        
        # Add assistant's answer to session history for future context
        session_history.append({
            "role": "assistant",
            "content": answer
        })



    


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
    setup_links_table()
    app()