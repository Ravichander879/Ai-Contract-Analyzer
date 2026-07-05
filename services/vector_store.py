import os
import json
import faiss
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer

# Cache the model in memory to avoid reloading it
_embedding_model = None

def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        # Load the sentence transformer model
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model

def chunk_document(pages_content: List[Dict[str, Any]], chunk_size: int = 700, chunk_overlap: int = 150) -> List[Dict[str, Any]]:
    """
    Chunks extracted page-by-page text.
    Tracks page number for each chunk.
    """
    chunks = []
    for page in pages_content:
        page_num = page["page_num"]
        text = page["text"]
        
        if not text:
            continue
            
        # Character-based splitting with overlap
        text_length = len(text)
        start = 0
        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunk_text = text[start:end].strip()
            
            # Only add chunks that contain text
            if len(chunk_text) > 10:
                chunks.append({
                    "text": chunk_text,
                    "page_num": page_num
                })
                
            if end == text_length:
                break
            start += (chunk_size - chunk_overlap)
            
    return chunks

def build_vector_store(contract_id: str, pages_content: List[Dict[str, Any]], base_dir: str = "vector_store") -> str:
    """
    Chunks document text, generates embeddings using SentenceTransformer,
    saves the FAISS index and the chunks metadata locally under base_dir/contract_id/
    """
    store_dir = os.path.join(base_dir, contract_id)
    os.makedirs(store_dir, exist_ok=True)
    
    # 1. Chunk text
    chunks = chunk_document(pages_content)
    if not chunks:
        # Create a fallback empty chunk if no text was found
        chunks = [{"text": "Empty document.", "page_num": 1}]
        
    # 2. Extract texts and generate embeddings
    texts = [c["text"] for c in chunks]
    model = get_embedding_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    
    # 3. Create FAISS index
    embeddings_np = np.array(embeddings).astype('float32')
    dimension = embeddings_np.shape[1]
    
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_np)
    
    # 4. Save index file
    index_path = os.path.join(store_dir, "index.faiss")
    faiss.write_index(index, index_path)
    
    # 5. Save metadata chunks json file
    metadata_path = os.path.join(store_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
        
    return store_dir

def query_vector_store(contract_id: str, query: str, k: int = 5, base_dir: str = "vector_store") -> List[Dict[str, Any]]:
    """
    Loads FAISS index and chunks metadata, embeds the query,
    performs similarity search and returns top k results.
    """
    store_dir = os.path.join(base_dir, contract_id)
    index_path = os.path.join(store_dir, "index.faiss")
    metadata_path = os.path.join(store_dir, "metadata.json")
    
    if not os.path.exists(index_path) or not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Vector store not found for contract: {contract_id}")
        
    # Load FAISS index
    index = faiss.read_index(index_path)
    
    # Load metadata
    with open(metadata_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
        
    # Embed query
    model = get_embedding_model()
    query_vector = model.encode([query], show_progress_bar=False).astype('float32')
    
    # Search index
    # We retrieve min(k, len(chunks)) to avoid index out of bounds errors
    k_retrieve = min(k, len(chunks))
    distances, indices = index.search(query_vector, k=k_retrieve)
    
    results = []
    for rank, idx in enumerate(indices[0]):
        if idx < 0 or idx >= len(chunks):
            continue
        chunk_info = chunks[idx]
        results.append({
            "text": chunk_info["text"],
            "page_num": chunk_info["page_num"],
            "distance": float(distances[0][rank])
        })
        
    return results
