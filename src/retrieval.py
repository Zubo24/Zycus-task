"""Module for chunking Knowledge Base docs and BM25 retrieval."""
# PRD Constraint: No vector DB / embeddings pipeline allowed. Using rank_bm25 for lightweight, deterministic keyword retrieval.

import os
import re
from rank_bm25 import BM25Okapi

_CHUNKS = []
_BM25_INDEX = None

def tokenize(text: str) -> list:
    """Simple alphanumeric tokenizer for BM25, splitting on punctuation and underscores."""
    return re.findall(r'[a-zA-Z0-9]+', text.lower())

def load_and_chunk_kb(kb_dir: str) -> list:
    """
    Loads all markdown files, splits on '---', and extracts the text, 
    source filename, and nearest preceding heading.
    """
    all_chunks = []
    for root, _, files in os.walk(kb_dir):
        for file in files:
            if not file.endswith('.md'):
                continue
            
            filepath = os.path.join(root, file)
            filename = os.path.basename(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            chunk_lines = []
            current_heading = ""
            chunk_heading = ""
            
            for line in lines:
                stripped = line.strip()
                # Split on horizontal rules
                if re.match(r'^---+$', stripped):
                    text = "\n".join(chunk_lines).strip()
                    if text:
                        h = chunk_heading if chunk_heading else current_heading
                        all_chunks.append({
                            "text": text,
                            "source_file": filename,
                            "heading": h
                        })
                    chunk_lines = []
                    chunk_heading = ""
                else:
                    if stripped.startswith("#"):
                        # Extract clean heading text (e.g. "## Setup" -> "Setup")
                        heading_text = stripped.lstrip("#").strip()
                        current_heading = heading_text
                        if not chunk_heading:
                            chunk_heading = heading_text
                    
                    chunk_lines.append(line.rstrip('\n'))
                    
            # Save the final chunk
            text = "\n".join(chunk_lines).strip()
            if text:
                h = chunk_heading if chunk_heading else current_heading
                all_chunks.append({
                    "text": text,
                    "source_file": filename,
                    "heading": h
                })
                
    return all_chunks

def build_index(kb_dir: str = None):
    """Build the BM25 index over the chunks."""
    global _CHUNKS, _BM25_INDEX
    
    if kb_dir is None:
        # Default to the project's knowledge_base directory
        kb_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge_base")
        
    _CHUNKS = load_and_chunk_kb(kb_dir)
    tokenized_corpus = [tokenize(c["text"]) for c in _CHUNKS]
    _BM25_INDEX = BM25Okapi(tokenized_corpus)

def search(query: str, top_k: int = 3) -> list:
    """Search the BM25 index and return the top_k matching chunks with scores."""
    if not _BM25_INDEX:
        build_index()
        
    tokenized_query = tokenize(query)
    scores = _BM25_INDEX.get_scores(tokenized_query)
    
    # Sort indices by descending score
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    
    results = []
    for idx in top_indices:
        if scores[idx] > 0:
            res = _CHUNKS[idx].copy()
            res["score"] = float(scores[idx])
            results.append(res)
            
    return results

if __name__ == "__main__":
    print("--- Sanity Checks for Retrieval ---")
    
    build_index()
    print(f"Index built with {len(_CHUNKS)} total chunks.")
    
    test_query = "connection timeout DataBridge"
    print(f"\nSearching for: '{test_query}'")
    
    results = search(test_query, top_k=3)
    for i, r in enumerate(results, 1):
        print(f"\nResult {i} (Score: {r['score']:.4f})")
        print(f"File: {r['source_file']}")
        print(f"Heading: {r['heading']}")
        
        # safely encode preview for Windows console
        preview = r['text'][:150].replace('\n', ' ') + "..."
        print(f"Preview: {preview.encode('ascii', 'ignore').decode('ascii')}")
