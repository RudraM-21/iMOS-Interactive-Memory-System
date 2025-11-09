import sqlite3
import typer
from .memory_db import setup_db, setup_links_table, add_memory, get_all_memories, get_linked_memories, search_memories_fast
import numpy as np
from .embedding import get_embedding
import json
import os
from .utils import extract_text_from_file
import requests
from dotenv import load_dotenv

load_dotenv()

# IMOS ASCII Logo
IMOS_LOGO = """
 ██╗███╗   ███╗ ██████╗ ███████╗
 ██║████╗ ████║██╔═══██╗██╔════╝
 ██║██╔████╔██║██║   ██║███████╗
 ██║██║╚██╔╝██║██║   ██║╚════██║
 ██║██║ ╚═╝ ██║╚██████╔╝███████║
 ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚══════╝
   IMOS: Solo Pro Memory OS
"""

def cosine_sim(a,b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# Create the main typer app with professional help text
app = typer.Typer(
    help="IMOS: Memory OS for Solo Professionals. Your thoughtful local memory assistant.",
    rich_markup_mode="rich"
)

@app.callback()
def main():
    """
    IMOS: Memory OS for Solo Professionals
    
    A thoughtful local memory assistant that helps you organize, search, and interact
    with your personal knowledge base through an intelligent CLI interface.
    """
    # Show logo on first run or help
    pass

def ensure_api_key():
    """Check if GROQ API key is configured"""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        typer.secho("\nIMOS Setup Required!", fg=typer.colors.YELLOW, bold=True)
        typer.echo("To use chat features, please set your GROQ API key:")
        typer.echo("  export GROQ_API_KEY='your-key-here'")
        typer.echo("  or add it to your .env file")
        typer.echo("\nGet your free API key at: https://console.groq.com/keys")
        raise typer.Exit(1)
    return groq_api_key

@app.command()
def add(text: str, source: str = "manual"):
    """Add a new memory to IMOS"""
    setup_db()
    setup_links_table()
    
    memory_id = add_memory(text=text, source=source)
    typer.secho(f"IMOS: Added memory #{memory_id}", fg=typer.colors.GREEN, bold=True)

@app.command()
def ask(query: str, top_k: int = 3, include_links: bool = True):
    """Ask IMOS a question and get relevant memories"""
    setup_db()
    setup_links_table()
    groq_api_key = ensure_api_key()
    
    # Display IMOS branding
    typer.secho("IMOS Memory Search", fg=typer.colors.BRIGHT_CYAN, bold=True)
    
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
        try:
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                typer.secho("IMOS Error: Invalid API key", fg=typer.colors.RED, bold=True)
                typer.echo("Please check your GROQ_API_KEY")
                raise typer.Exit(1)
            else:
                raise e

    answer = get_llm_response(full_prompt, groq_api_key)
    typer.secho("\nIMOS>", fg=typer.colors.BRIGHT_CYAN, bold=True)
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
       typer.secho("\nPrimary sources:", fg=typer.colors.BLUE, bold=True)
       for src in primary_sources:
        if os.path.exists(src):
            abs_path = os.path.abspath(src)
            typer.echo(f"  • {abs_path}")
        else:
            typer.echo(f"  • {src}")
    
    if linked_sources:
       typer.secho("\nRelated memories (auto-linked):", fg=typer.colors.MAGENTA, bold=True)
       for src in linked_sources:
        if os.path.exists(src):
            abs_path = os.path.abspath(src)
            typer.echo(f"  • {abs_path}")
        else:
            typer.echo(f"  • {src}")

@app.command()
def chat(top_k: int = 3, include_links: bool = True):
    """
    Start IMOS in interactive chat mode
    
    Have a conversation with your memory assistant. Type 'exit' or 'quit' to stop.
    IMOS will remember context within the session for richer conversations.
    """
    setup_db()
    setup_links_table()
    groq_api_key = ensure_api_key()

    # Display startup message with branding
    typer.echo(IMOS_LOGO)
    typer.secho("IMOS Chat Mode Active", fg=typer.colors.BRIGHT_CYAN, bold=True)
    typer.echo("Type your question; type 'exit' to leave.\n")

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
                typer.secho("IMOS: Context too long, trimming conversation history...", fg=typer.colors.YELLOW)
                return "I notice our conversation is getting quite long. Let me reset to keep things flowing smoothly. What was your question again?"
            elif e.response.status_code == 429:  # Rate limit
                typer.secho("IMOS: API rate limit hit. Please wait a moment and try again...", fg=typer.colors.YELLOW)
                return "I'm hitting the API rate limit. Please wait a few seconds and ask your question again."
            elif e.response.status_code == 401:
                typer.secho("IMOS Error: Invalid API key", fg=typer.colors.RED, bold=True)
                typer.echo("Please check your GROQ_API_KEY")
                raise typer.Exit(1)
            else:
                typer.secho(f"IMOS: API Error {e.response.status_code}: {e.response.reason}", fg=typer.colors.RED)
                return f"Sorry, I encountered an API error. Please try again in a moment."

    def trim_session_history(session_history, max_messages=8):
        """Keep only system prompt + recent messages to prevent context overflow"""
        if len(session_history) <= max_messages:
            return session_history
        
        # Always keep system prompt (first message) + recent messages
        system_prompt = session_history[0]
        recent_messages = session_history[-(max_messages-1):]
        return [system_prompt] + recent_messages

    while True:
        try:
            query = input("imos> ").strip()
        except KeyboardInterrupt:
            print("\nExiting IMOS Chat. Goodbye!")
            break
            
        if query.lower() in ["exit", "quit", "bye"]:
            typer.secho("Exiting IMOS Chat. Your memories remain safe!", fg=typer.colors.GREEN)
            break

        if not query:
            continue

        # Echo back the user's question for better conversation flow
        typer.secho(f"\nYou: {query}", fg=typer.colors.WHITE, bold=True)

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
        typer.secho("\nIMOS>", fg=typer.colors.BRIGHT_CYAN, bold=True)
        typer.echo(f"{answer}\n")

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
         typer.secho("Primary sources:", fg=typer.colors.BLUE)
         for src in primary_sources:
          if os.path.exists(src):
            abs_path = os.path.abspath(src)
            typer.echo(f"  • {abs_path}")
          else:
            typer.echo(f"  • {src}")
        
        if linked_sources:
         typer.secho("Related memories (auto-linked):", fg=typer.colors.MAGENTA)
         for src in linked_sources:
          if os.path.exists(src):
            abs_path = os.path.abspath(src)
            typer.echo(f"  • {abs_path}")
          else:
            typer.echo(f"  • {src}")

        print()  # Add spacing between turns
        
        # Add assistant's answer to session history for future context
        session_history.append({
            "role": "assistant",
            "content": answer
        })

@app.command()
def actions():
    """List all open action items detected from your knowledge"""
    setup_db()
    setup_links_table()
    
    conn = sqlite3.connect("memory.db")
    c = conn.cursor()
    c.execute("SELECT id, action_text, source, created_at FROM actions WHERE status = 'open'")
    actions_list = c.fetchall()
    
    if not actions_list:
        typer.secho("IMOS: No open actions! You're on top of things.", fg=typer.colors.GREEN, bold=True)
    else:
        typer.secho("IMOS: Open Action Items", fg=typer.colors.YELLOW, bold=True)
        typer.echo("=" * 50)
        for aid, text, src, dt in actions_list:
            typer.echo(f"[{aid}] {text}")
            typer.secho(f"    Source: {src} | Added: {dt[:10]}", fg=typer.colors.BLUE)
            
    conn.close()

@app.command()
def done(action_id: int):
    """Mark an action as completed"""
    setup_db()
    setup_links_table()
    
    conn = sqlite3.connect("memory.db")
    c = conn.cursor()
    c.execute("UPDATE actions SET status = 'done' WHERE id=?", (action_id,))
    conn.commit()
    
    if c.rowcount > 0:
        typer.secho(f"IMOS: Action {action_id} marked as done!", fg=typer.colors.GREEN, bold=True)
    else:
        typer.secho(f"IMOS: Action {action_id} not found", fg=typer.colors.RED)
        
    conn.close()

@app.command()
def addfile(path: str):
    """Import a file into IMOS memory"""
    setup_db()
    setup_links_table()
    
    try:
        text = extract_text_from_file(path)
        memory_id = add_memory(text, source=path)
        typer.secho(f"IMOS: Imported '{path}' as memory #{memory_id}", fg=typer.colors.GREEN, bold=True)
    except Exception as e:
        typer.secho(f"IMOS Error: Could not import file - {e}", fg=typer.colors.RED, bold=True)

@app.command()
def import_folder(path: str):
    """
    Import all supported files from a directory into IMOS memory
    
    Recursively imports .txt, .pdf, .docx files from the specified directory.
    """
    setup_db()
    setup_links_table()
    
    if not os.path.exists(path):
        typer.secho(f"IMOS Error: Directory '{path}' not found", fg=typer.colors.RED, bold=True)
        raise typer.Exit(1)

    imported = 0
    failed = 0

    typer.secho(f"IMOS: Importing files from '{path}'...", fg=typer.colors.BLUE, bold=True)
    
    for root, dirs, files in os.walk(path):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in [".txt", ".pdf", ".docx"]:
                fpath = os.path.join(root, fname)
                try:
                    text = extract_text_from_file(fpath)
                    add_memory(text, source=fpath)
                    imported += 1
                    typer.secho(f"  ✓ Imported: {fpath}", fg=typer.colors.GREEN)
                except Exception as e:
                    failed += 1
                    typer.secho(f"  ✗ Error with {fpath}: {e}", fg=typer.colors.RED)
    
    typer.secho(f"\nIMOS: Import complete! {imported} files imported, {failed} failed", 
                fg=typer.colors.BRIGHT_CYAN, bold=True)

@app.command()
def list():
    """List all stored memories with ID and preview"""
    setup_db()
    setup_links_table()
    
    memories = get_all_memories()
    
    if not memories:
        typer.secho("IMOS: No memories found. Use 'imos add' or 'imos addfile' to get started!", 
                   fg=typer.colors.YELLOW)
        return
        
    typer.secho("IMOS: Your Memory Library", fg=typer.colors.BRIGHT_CYAN, bold=True)
    typer.echo("=" * 60)
    
    for memory in memories:
        snippet = memory["text"][:60].replace('\n', ' ')
        source = memory.get("source", "manual")
        typer.echo(f"[{memory['id']:>3}] {snippet}" + ("..." if len(memory["text"]) > 60 else ""))
        typer.secho(f"      Source: {source}", fg=typer.colors.BLUE)

@app.command()
def links(id: int):
    """Show linked memories for a specific memory ID"""
    setup_db()
    setup_links_table()
    
    conn = sqlite3.connect("memory.db")
    c = conn.cursor()
    c.execute("SELECT target_id, similarity FROM memory_links WHERE source_id=?", (id,))
    linked = c.fetchall()
    conn.close()
    
    if not linked:
        typer.secho(f"IMOS: No linked memories found for memory #{id}", fg=typer.colors.YELLOW)
        return
        
    typer.secho(f"IMOS: Memories linked to #{id}", fg=typer.colors.BRIGHT_CYAN, bold=True)
    for tgt, sim in linked:
        typer.echo(f"  Linked to #{tgt} (similarity: {sim:.2f})")

@app.command()
def rebuild_links(threshold: float = 0.85):
    """
    Rebuild all memory links based on similarity
    
    This process analyzes all memories and creates links between similar ones.
    Run this after bulk imports or to refresh connections.
    """
    setup_db()
    setup_links_table()
    
    from .memory_db import auto_link_memory
    
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
    
    if total == 0:
        typer.secho("IMOS: No memories to link", fg=typer.colors.YELLOW)
        return
        
    typer.secho(f"IMOS: Rebuilding links for {total} memories (threshold={threshold})...", 
               fg=typer.colors.BLUE, bold=True)
    
    with typer.progressbar(all_memories, label="Processing memories") as progress:
        for mid, emb_str in progress:
            emb = np.array(json.loads(emb_str))
            auto_link_memory(mid, emb, threshold=threshold)
    
    typer.secho(f"\nIMOS: Successfully rebuilt all memory links!", fg=typer.colors.GREEN, bold=True)

def main_cli():
    """Entry point for console script"""
    setup_db()
    setup_links_table()
    app()

if __name__ == "__main__":
    main_cli()