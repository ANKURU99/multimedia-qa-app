from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from backend.app.services.rag_engine import RAGEngine

router = APIRouter(tags=["AI Chat & Summary"])
rag_engine = RAGEngine()

class ChatRequest(BaseModel):
    file_id: str
    query: str

@router.post("/query")
async def query_knowledge_base(request: ChatRequest):
    """
    Queries the vector database using context matching and prompts the LLM
    to generate an answer complete with source citations.
    """
    try:
        response_data = rag_engine.generate_answer(
            query=request.query, 
            file_id=request.file_id
        )
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG Engine error: {str(e)}")

@router.get("/summary/{file_id}")
async def get_file_summary(file_id: str):
    """
    Retrieves knowledge chunks tied to the file_id to build a comprehensive summary.
    """
    try:
        summary_text = rag_engine.generate_summary(file_id=file_id)
        return {"file_id": file_id, "summary": summary_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary generation error: {str(e)}")
        