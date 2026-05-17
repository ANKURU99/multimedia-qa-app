import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.app.config import settings
from backend.app.services.pdf_worker import PDFWorker
from backend.app.services.media_worker import MediaWorker
from backend.app.database import vector_db

router = APIRouter(prefix="/upload", tags=["Upload System"])
media_worker = MediaWorker()

@router.post("/file")
async def upload_file(file: UploadFile = File(...)):
    """
    Accepts PDF, MP3, or MP4 files, processes their content/timestamps into chunks,
    and indexes them inside the local Vector DB.
    """
    filename = file.filename
    file_ext = os.path.splitext(filename)[1].lower()
    
    if file_ext not in [".pdf", ".mp3", ".mp4"]:
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file format. Please upload a .pdf, .mp3, or .mp4 file."
        )
        
    # Generate a completely unique file tracking identifier
    file_id = str(uuid.uuid4())
    saved_file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{file_ext}")
    
    # Save the file stream chunks down onto our disk
    try:
        with open(saved_file_path, "wb") as buffer:
            while content := await file.read(1024 * 64):
                buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file to storage disk: {str(e)}")

    # Extract text/timestamps depending on what type of file came down the pipeline
    try:
        if file_ext == ".pdf":
            chunks = PDFWorker.extract_and_chunk(saved_file_path)
        else:
            chunks = media_worker.transcribe_with_timestamps(saved_file_path)
            
        if not chunks:
            raise ValueError("No text or audio segments could be extracted from this asset.")
            
        # Write the extracted knowledge blocks directly into ChromaDB
        vector_db.add_documents(chunks, file_id=file_id)
        
    except Exception as e:
        # Clean up the broken file if something crashes during vector indexing
        if os.path.exists(saved_file_path):
            os.remove(saved_file_path)
        raise HTTPException(status_code=500, detail=f"File parsing failure: {str(e)}")

    return {
        "message": "File processed and indexed successfully.",
        "file_id": file_id,
        "filename": filename,
        "type": "document" if file_ext == ".pdf" else "media"
    }
    