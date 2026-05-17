import os
from pypdf import PdfReader

class PDFWorker:
    @staticmethod
    def extract_and_chunk(file_path: str, chunk_size: int = 500, chunk_overlap: int = 100) -> list[dict]:
        """
        Reads a PDF file, extracts text page by page, and breaks it into overlapping 
        chunks. Returns a list of dictionaries with text and metadata.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at: {file_path}")
            
        reader = PdfReader(file_path)
        chunks = []
        
        for page_idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            page_number = page_idx + 1
            
            # Clean up whitespace formatting
            page_text = " ".join(page_text.split())
            
            # Simple character-based sliding window chunking
            start = 0
            while start < len(page_text):
                end = start + chunk_size
                chunk_text = page_text[start:end]
                
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "source_type": "pdf",
                        "page": page_number,
                        "file_path": file_path
                    }
                })
                
                # Move window forward by chunk_size minus overlap
                start += (chunk_size - chunk_overlap)
                if chunk_size >= len(page_text[start:]):
                    break
                    
        return chunks
        