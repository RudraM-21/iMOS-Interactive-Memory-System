import fitz
from docx import Document

def extract_text_from_file(path):
    """Extract text from various file formats"""
    if path.endswith(".txt"):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    
    elif path.endswith(".pdf"):
        doc = fitz.open(path)
        text = "\n".join([page.get_text() for page in doc])
        doc.close()
        return text
    
    elif path.endswith(".docx"):
        doc = Document(path) 
        return "\n".join([para.text for para in doc.paragraphs])
    else:
        raise ValueError("Unsupported file type: " + path)