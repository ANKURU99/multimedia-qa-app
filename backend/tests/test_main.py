import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from backend.app.main import app
from backend.app.config import settings
from backend.app.services.pdf_worker import PDFWorker
from backend.app.services.media_worker import MediaWorker
from backend.app.services.rag_engine import RAGEngine
from backend.app.database import vector_db

client = TestClient(app)

# ==================== BASELINE GATEWAY TESTS ====================

def test_root_endpoint():
    """Verify core gateway health metrics."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

# ==================== WORKER UNIT TESTS ====================

def test_pdf_worker_missing_file():
    """Ensure workers properly handle missing physical path pointers."""
    with pytest.raises(FileNotFoundError):
        PDFWorker.extract_and_chunk("non_existent_file.pdf")

@patch("backend.app.services.pdf_worker.PdfReader")
def test_pdf_worker_extraction_flow(mock_pdf_reader):
    """Force execution of the PDF page splitting sliding window logic."""
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "This is sample project data to hit coverage limits."
    mock_reader_instance = MagicMock()
    mock_reader_instance.pages = [mock_page]
    mock_pdf_reader.return_value = mock_reader_instance

    dummy_path = "dummy_test_file.pdf"
    with open(dummy_path, "w") as f:
        f.write("dummy content")

    try:
        chunks = PDFWorker.extract_and_chunk(dummy_path, chunk_size=10, chunk_overlap=2)
        assert len(chunks) > 0
    finally:
        if os.path.exists(dummy_path):
            os.remove(dummy_path)

def test_media_worker_missing_file():
    """Ensure media workers throw accurate exceptions for missing assets."""
    worker = MediaWorker()
    with pytest.raises(FileNotFoundError):
        worker.transcribe_with_timestamps("missing_audio.mp3")

@patch("backend.app.services.media_worker.OpenAI")
def test_media_worker_live_api_mock(mock_openai_client):
    """Force execution of the live OpenAI Whisper API branch inside MediaWorker."""
    with patch.object(settings, "OPENAI_API_KEY", "real-style-api-key-structure"):
        mock_segment = MagicMock()
        mock_segment.get.side_effect = lambda key, default=None: {
            "text": "Sample whisper audio sentence extraction.",
            "start": 1.2,
            "end": 5.4
        }.get(key, default)
        
        mock_response = MagicMock()
        mock_response.segments = [mock_segment]
        mock_openai_client.return_value.audio.transcriptions.create.return_value = mock_response
        
        worker = MediaWorker()
        dummy_path = "dummy_audio.mp3"
        with open(dummy_path, "w") as f:
            f.write("dummy audio data")
            
        try:
            chunks = worker.transcribe_with_timestamps(dummy_path)
            assert len(chunks) > 0
        finally:
            if os.path.exists(dummy_path):
                os.remove(dummy_path)

def test_media_worker_mock_path_fallback():
    """Force execution of the local Whisper backup generator path."""
    worker = MediaWorker()
    dummy_path = "dummy_audio.mp3"
    with open(dummy_path, "w") as f:
        f.write("dummy audio content")

    try:
        chunks = worker.transcribe_with_timestamps(dummy_path)
        assert len(chunks) > 0
    finally:
        if os.path.exists(dummy_path):
            os.remove(dummy_path)

# ==================== DATABASE & RAG ENGINE TESTS ====================

@patch("backend.app.services.rag_engine.OpenAI")
@patch("backend.app.database.VectorDatabase.query_similarity")
def test_rag_engine_production_branches(mock_query, mock_openai):
    """Force execution of live production OpenAI generation branches for chat and summary."""
    with patch.object(settings, "OPENAI_API_KEY", "real-style-api-key-structure"):
        mock_query.return_value = [{"text": "Found context.", "metadata": {"source_type": "pdf", "page": 2}}]
        
        mock_choice = MagicMock()
        mock_choice.message.content = "This is a real live structured response."
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        engine = RAGEngine()
        res = engine.generate_answer("Test question?", "file-id")
        assert "answer" in res

@patch("backend.app.database.chromadb.PersistentClient")
def test_rag_engine_fallback_flows(mock_chroma):
    """Verify fallback response handling configurations and empty mock elements."""
    engine = RAGEngine()
    
    # Force mock media source citation paths
    mock_sources = [{"source_type": "media", "start_time": 65.0}]
    res = engine._generate_mock_rag_response("Query text", mock_sources)
    assert "01:05" in res["answer"]

    # Verify summary with mock collection objects
    with patch.object(vector_db.collection, "get", return_value={"documents": []}):
        summary = engine.generate_summary("test-file-id")
        assert "No content found" in summary

    summary = engine.generate_summary("test-file-id")
    assert "mock summary" in summary.lower()

def test_database_empty_query_safeguard():
    """Directly execute empty or unmatched collection queries inside database.py lines 54-55."""
    with patch.object(vector_db.collection, "query", return_value={"documents": [[]], "metadatas": [[]]}):
        res = vector_db.query_similarity("empty test", "file-id")
        assert res == []

# ==================== HTTP ENDPOINT ROUTER TESTS ====================

def test_upload_unsupported_file_type():
    """Verify that the ingestion gateway blocks invalid extensions."""
    files = {"file": ("test.txt", b"dummy text content", "text/plain")}
    response = client.post("/upload/file", files=files)
    assert response.status_code == 400

@patch("backend.app.routes.upload.PDFWorker.extract_and_chunk")
def test_successful_pdf_upload_route(mock_extract):
    """Simulate a flawless end-to-end multi-part form upload stream."""
    mock_extract.return_value = [{"text": "Mock data.", "metadata": {"source_type": "pdf", "page": 1, "file_path": "fake.pdf"}}]
    files = {"file": ("sample_document.pdf", b"%PDF-1.4 data stream", "application/pdf")}
    response = client.post("/upload/file", files=files)
    assert response.status_code == 200

@patch("backend.app.routes.upload.open")
def test_upload_write_disk_failure(mock_open):
    """Triggers disk write exception handlers in upload.py line 36-37."""
    mock_open.side_effect = IOError("Simulated disk error")
    files = {"file": ("sample.pdf", b"data", "application/pdf")}
    response = client.post("/upload/file", files=files)
    assert response.status_code == 500

@patch("backend.app.routes.upload.PDFWorker.extract_and_chunk")
def test_upload_route_parsing_failure(mock_extract):
    """Triggers exception handling block in upload.py lines 44-47."""
    mock_extract.return_value = [] # Return empty array to raise parsing ValueError
    files = {"file": ("sample.pdf", b"data", "application/pdf")}
    response = client.post("/upload/file", files=files)
    assert response.status_code == 500

@patch("backend.app.routes.chat.RAGEngine.generate_answer")
def test_chat_query_endpoint_failures(mock_answer):
    """Trigger HTTP 500 server exceptions inside chat router query endpoints."""
    mock_answer.side_effect = Exception("System RAG Error")
    payload = {"file_id": "id", "query": "text"}
    response = client.post("/query", json=payload)
    assert response.status_code == 500

@patch("backend.app.routes.chat.RAGEngine.generate_summary")
def test_summary_generation_endpoint_failures(mock_summary):
    """Trigger HTTP 500 server exceptions inside chat router summary endpoints."""
    mock_summary.side_effect = Exception("System Summary Error")
    response = client.get("/summary/mock-id")
    assert response.status_code == 500

def test_successful_endpoints():
    """Verify happy path router logic outputs."""
    payload = {"file_id": "mock-id", "query": "test query"}
    assert client.post("/query", json=payload).status_code == 200
    assert client.get("/summary/mock-id").status_code == 200