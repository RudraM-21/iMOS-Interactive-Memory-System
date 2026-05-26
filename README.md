# IMOS: Memory OS for Solo Professionals

```
 ██╗███╗   ███╗ ██████╗ ███████╗
 ██║████╗ ████║██╔═══██╗██╔════╝
 ██║██╔████╔██║██║   ██║███████╗
 ██║██║╚██╔╝██║██║   ██║╚════██║
 ██║██║ ╚═╝ ██║╚██████╔╝███████║
 ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚══════╝
   IMOS: Solo Pro Memory OS
```

**IMOS** is your thoughtful local memory assistant - a powerful CLI tool that helps solo professionals organize, search, and interact with their personal knowledge base through intelligent semantic search and AI-powered conversations.

## Features

- **Smart Memory Search**: Semantic search across your personal knowledge base
- **AI-Powered Chat**: Interactive conversations with your memories using Groq LLM
- **Automatic File Import**: Support for .txt, .pdf, and .docx files
- **Action Item Tracking**: Automatically detects and tracks TODOs from your notes
- **Memory Linking**: Automatically connects related memories for richer context
- **Beautiful CLI**: Professional, colored terminal interface with clear branding
- **Fast & Efficient**: Vectorized operations and model caching for lightning-fast responses

## Quick Start

### Installation

```bash
pip install imos
```

### Setup

1. Get your free API key from [Groq Console](https://console.groq.com/keys)

2. Set your API key:
```bash
export GROQ_API_KEY="your-key-here"
```

Or create a `.env` file:
```bash
echo "GROQ_API_KEY=your-key-here" > .env
```

### Basic Usage

```bash
# Start an interactive chat with your memories
imos chat

# Ask a quick question
imos ask "What are my project goals?"

# Import a file
imos addfile notes.txt

# Import an entire folder
imos import-folder ~/Documents/Notes

# View action items
imos actions

# List all memories
imos list
```

## Usage Examples

### Interactive Chat Mode
```bash
$ imos chat
 ██╗███╗   ███╗ ██████╗ ███████╗
 ██║████╗ ████║██╔═══██╗██╔════╝
 ██║██╔████╔██║██║   ██║███████╗
 ██║██║╚██╔╝██║██║   ██║╚════██║
 ██║██║ ╚═╝ ██║╚██████╔╝███████║
 ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚══════╝
   IMOS: Solo Pro Memory OS

IMOS Chat Mode Active
Type your question; type 'exit' to leave.

imos> What are my main project goals for this quarter?

You: What are my main project goals for this quarter?

IMOS> Based on your notes, your main project goals for this quarter include...

Primary sources:
  • /Users/you/Documents/Q4-Goals.txt
  • /Users/you/Notes/project-planning.md
```

### Quick Questions
```bash
$ imos ask "What did I learn about Python optimization?"
IMOS Memory Search
Loading embedding model (one-time setup)...

IMOS> From your notes, you learned several key Python optimization techniques...

Primary sources:
  • /Users/you/Notes/python-performance.md
  • /Users/you/Documents/coding-tips.txt
```

### File Import
```bash
$ imos import-folder ~/Documents/ProjectNotes
IMOS: Importing files from '/Users/you/Documents/ProjectNotes'...
  ✓ Imported: /Users/you/Documents/ProjectNotes/ideas.txt
  ✓ Imported: /Users/you/Documents/ProjectNotes/research.pdf
  ✓ Imported: /Users/you/Documents/ProjectNotes/meeting-notes.docx

IMOS: Import complete! 3 files imported, 0 failed
```

### Action Tracking
```bash
$ imos actions
IMOS: Open Action Items
==================================================
[1] Review quarterly performance metrics
    Source: /Users/you/Notes/q4-review.txt | Added: 2024-11-09

[2] Follow up with client about project timeline
    Source: manual | Added: 2024-11-08

$ imos done 1
IMOS: Action 1 marked as done!
```

## Commands Reference

| Command | Description |
|---------|-------------|
| `imos chat` | Start interactive chat mode |
| `imos ask "question"` | Ask a quick question |
| `imos add "text"` | Add a memory manually |
| `imos addfile path/to/file` | Import a single file |
| `imos import-folder path/` | Import all supported files from a directory |
| `imos actions` | List all open action items |
| `imos done <id>` | Mark an action as completed |
| `imos list` | List all stored memories |
| `imos rebuild-links` | Rebuild memory connections |

## Configuration

### Environment Variables

- `GROQ_API_KEY`: Your Groq API key (required for chat features)

### File Support

IMOS automatically extracts text from:
- `.txt` files (plain text)
- `.pdf` files (via PyMuPDF)
- `.docx` files (Microsoft Word documents)

### Data Storage

- Memories are stored in a local SQLite database (`memory.db`)
- Embeddings use the `all-MiniLM-L6-v2` model for fast, efficient semantic search
- No data is sent to external services except for LLM chat queries

## Performance Features

- **Model Caching**: Embedding model loads once and stays in memory
- **Vectorized Search**: NumPy-optimized similarity calculations
- **Smart Context Management**: Automatic conversation history trimming
- **Deduplication**: Prevents storing duplicate content

## Privacy & Security

- All your memories stay local in SQLite database
- Only chat queries are sent to Groq's API for processing
- No tracking or analytics
- Open source and transparent

## Troubleshooting

### Missing API Key
```
IMOS Setup Required!
To use chat features, please set your GROQ API key:
  export GROQ_API_KEY='your-key-here'
  or add it to your .env file

Get your free API key at: https://console.groq.com/keys
```

### Installation Issues
```bash
# Upgrade pip first
pip install --upgrade pip

# Install with verbose output for debugging
pip install -v imos
```

### File Import Errors
- Ensure files are not corrupted
- Check file permissions
- Verify file format is supported (.txt, .pdf, .docx)

## Development & Contributing

IMOS is open source! Visit our [GitHub repository](https://github.com/RudraM-21/IMOS_terminal) to:
- Report issues
- Submit feature requests  
- Contribute code
- View the source

## Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/RudraM-21/IMOS_terminal/issues)
- **Documentation**: This README and `imos --help`
- **Community**: Join discussions in our GitHub repository

## License

IMOS is released under the MIT License. See LICENSE for details.

---

**IMOS: Your memories, organized intelligently.**