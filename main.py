import typer
from memory_db import setup_db, add_memory

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


if __name__ == "__main__" :
    setup_db()
    app()