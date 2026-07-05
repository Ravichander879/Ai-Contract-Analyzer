import os
import fitz # PyMuPDF
from typing import List, Dict, Any

def extract_text_by_page(file_path: str) -> List[Dict[str, Any]]:
    """
    Extracts text page-by-page from a PDF contract.
    Returns a list of dicts: [{'page_num': 1, 'text': '...'}, ...]
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found at: {file_path}")

    pages_content = []
    
    # Open PDF document
    doc = fitz.open(file_path)
    try:
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_text = page.get_text()
            pages_content.append({
                "page_num": page_idx + 1,
                "text": page_text.strip()
            })
    finally:
        doc.close()
        
    return pages_content

def get_pdf_metadata(file_path: str) -> Dict[str, Any]:
    """
    Retrieves metadata about the PDF (number of pages, file size in KB).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found at: {file_path}")
        
    file_size_kb = round(os.path.getsize(file_path) / 1024, 2)
    
    doc = fitz.open(file_path)
    page_count = len(doc)
    doc.close()
    
    return {
        "pages": page_count,
        "size_kb": file_size_kb,
        "filename": os.path.basename(file_path)
    }
