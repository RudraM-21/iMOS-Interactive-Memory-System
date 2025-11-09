import sqlite3
import typer
from memory_db import setup_db, setup_links_table, add_memory, get_all_memories, get_linked_memories, search_memories_fast
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
def ask(query: str, top_k: int=3, include_links: bool=True):
    """Ask IMOS a question, returns the most relevant memories."""
    
    query_emb = np.array(json.loads(get_embedding(query)))
    
    # Use fast vectorized search instead of loading all memories
    top_memories = search_memories_fast(query_emb, top_k)
    
    # Expand with linked memories if enabled
    all_context_memories = []
    linked_memory_ids = set()
    
    for mem in top_memories:
        all_context_memories.append(mem)
        
        if include_links:
            linked = get_linked_memories(mem["id"])
            for linked_mem in linked:
                if linked_mem["id"] not in linked_memory_ids:
                    all_context_memories.append(linked_mem)
                    linked_memory_ids.add(linked_mem["id"])

    def build_prompt(query, memory_list):
        prompt = (
            f"You are IMOS, a thoughtful local memory assistant.\n"
            f"A user asked: '{query}'\n\n"
            f"Here are notes and ideas from their personal library.\n"
        )
        for memory in memory_list:
            source = memory.get("source","manual")
            txt = memory["text"].replace("\n", " ")
            # Mark linked memories differently
            link_tag = " [LINKED]" if memory.get("link_similarity") else ""
            prompt += f"- [{source}]{link_tag} : {txt}\n"
        prompt += (
            "\nPlease answer conversationally (like a friend or coach), weaving key insights."
            "Reference their notes (use file names if useful), and avoid robotic tone."
        )
        return prompt
    
    full_prompt = build_prompt(query, all_context_memories)

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
    
    # Separate primary and linked sources
    primary_sources = []
    linked_sources = []
    
    for mem in top_memories:
        src = mem.get("source", "manual")
        if src not in primary_sources:
           primary_sources.append(src)
    
    for mem in all_context_memories:
        if mem.get("link_similarity"):  # It's a linked memory
            src = mem.get("source", "manual")
            if src not in linked_sources and src not in primary_sources:
                linked_sources.append(src)

    if primary_sources:
       print("\n📚 Primary sources:")
       for src in primary_sources:
        if os.path.exists(src):
            abs_path = os.path.abspath(src)
            print(f"  • {abs_path}")
        else:
            print(f"  • {src}")
    
    if linked_sources:
       print("\n🔗 Related memories (auto-linked):")
       for src in linked_sources:
        if os.path.exists(src):
            abs_path = os.path.abspath(src)
            print(f"  • {abs_path}")
        else:
            print(f"  • {src}")




@app.command()
def chat(top_k: int = 3, include_links: bool = True):
    """
    Start IMOS in chat mode. You can ask multiple questions. Type 'exit' or 'quit' to stop.
    Now supports multi-turn session context for richer, conversational answers.
    """

    groq_api_key = os.getenv("GROQ_API_KEY")
    print("IMOS Chat Mode. Type your question; type 'exit' to leave.")

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
            link_tag = " [LINKED]" if mem.get("link_similarity") else ""
            prompt += f"- [{source}]{link_tag}: {txt}\n"
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
        
        try:
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 413:  # Payload too large
                print("⚠️  Context too long, trimming conversation history...")
                return "I notice our conversation is getting quite long. Let me reset to keep things flowing smoothly. What was your question again?"
            elif e.response.status_code == 429:  # Rate limit
                print("⚠️  API rate limit hit. Please wait a moment and try again...")
                return "I'm hitting the API rate limit. Please wait a few seconds and ask your question again."
            else:
                print(f"⚠️  API Error {e.response.status_code}: {e.response.reason}")
                return f"Sorry, I encountered an API error. Please try again in a moment."

    def trim_session_history(session_history, max_messages=6):
        """Keep only system prompt + recent messages to prevent context overflow"""
        if len(session_history) <= max_messages:
            return session_history
        
        # Always keep system prompt (first message) + recent messages
        system_prompt = session_history[0]
        recent_messages = session_history[-(max_messages-1):]
        return [system_prompt] + recent_messages

    while True:
        query = input("imos> ").strip()
        if query.lower() in ["exit", "quit"]:
            print("Exiting IMOS Chat. All recent conversations are in your log (if enabled).")
            break

        # Echo back the user's question for better conversation flow
        print(f"\nYou: {query}")

        query_emb = np.array(json.loads(get_embedding(query)))
        # Use fast vectorized search instead of loading all memories
        top_memories = search_memories_fast(query_emb, top_k)
        
        # Expand with linked memories
        all_context_memories = []
        linked_memory_ids = set()
        
        for mem in top_memories:
            all_context_memories.append(mem)
            
            if include_links:
                linked = get_linked_memories(mem["id"])
                for linked_mem in linked:
                    if linked_mem["id"] not in linked_memory_ids:
                        all_context_memories.append(linked_mem)
                        linked_memory_ids.add(linked_mem["id"])

        # Build memory context (relevant memories)
        memory_context = build_memory_context(query, all_context_memories)

        # Add this turn to session: user question with memory context
        session_history.append({
            "role": "user",
            "content": f"{query}\n\n{memory_context}"
        })

        # Trim history to prevent context overflow
        session_history = trim_session_history(session_history, max_messages=8)

        # Get LLM answer from Groq, given all session context so far
        answer = get_llm_response(session_history, groq_api_key)

        # Print the answer (conversational, context-aware)
        print("\nIMOS>", answer)

        # Separate primary and linked sources
        primary_sources = []
        linked_sources = []
        
        for mem in top_memories:
           src = mem.get("source", "manual")
           if src not in primary_sources:
               primary_sources.append(src)
        
        for mem in all_context_memories:
            if mem.get("link_similarity"):
                src = mem.get("source", "manual")
                if src not in linked_sources and src not in primary_sources:
                    linked_sources.append(src)

        if primary_sources:
         print("\n📚 Primary sources:")
         for src in primary_sources:
          if os.path.exists(src):
            abs_path = os.path.abspath(src)
            print(f"  • {abs_path}")
          else:
            print(f"  • {src}")
        
        if linked_sources:
         print("\n🔗 Related memories (auto-linked):")
         for src in linked_sources:
          if os.path.exists(src):
            abs_path = os.path.abspath(src)
            print(f"  • {abs_path}")
          else:
            print(f"  • {src}")

        
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
def rebuild_links(threshold: float = 0.85):
    """
    Rebuild all memory links (slow for large databases).
    Run this after bulk imports or periodically to find related memories.
    Use --threshold to adjust similarity threshold (0.0-1.0, default 0.85).
    """
    from memory_db import auto_link_memory
    
    conn = sqlite3.connect("memory.db")
    c = conn.cursor()
    
    # Clear existing links
    c.execute("DELETE FROM memory_links")
    conn.commit()
    
    # Get all memories
    c.execute("SELECT id, embedding FROM memories")
    all_memories = c.fetchall()
    conn.close()
    
    total = len(all_memories)
    typer.echo(f"Rebuilding links for {total} memories (threshold={threshold})...")
    
    for idx, (mid, emb_str) in enumerate(all_memories, 1):
        emb = np.array(json.loads(emb_str))
        auto_link_memory(mid, emb, threshold=threshold)
        
        # Progress indicator
        if idx % 10 == 0 or idx == total:
            typer.echo(f"  Progress: {idx}/{total}")
    
    typer.secho(f"\n✅ Done! Rebuilt all memory links.", fg=typer.colors.GREEN)


@app.command()
def list():
    """List all stored memories (ID, text, summary)."""
    memories = get_all_memories()
    for memory in memories:
        snippet = memory["text"][:60].replace('\n',' ')
        typer.echo(f"[{memory['id']:>3}] {snippet}" + ("..." if len(memory["text"]) > 60 else ""))


@app.command()
def actions():
    """List all open actions items detected from your knowledge."""

    conn = sqlite3.connect("memory.db")
    c = conn.cursor()
    c.execute("SELECT id, action_text, source, created_at FROM actions WHERE status = 'open'")
    actions = c.fetchall()
    if not actions:
        print("No open actions! You're on top of things.")
    else :
        print("Open Actions Items:")
        for aid, text, src, dt in actions:
            print(f"[{aid}] {text} (source: {src}, added: {dt[:10]})")
    conn.close()
              

@app.command()
def done(action_id:int):
    """Mark an action as completed"""

    conn = sqlite3.connect("memory.db")
    c = conn.cursor()
    c.execute("UPDATE actions SET status = 'done' WHERE id=?",(action_id,))
    conn.commit()
    print(f"Action {action_id} marked as done.")
    conn.close()


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