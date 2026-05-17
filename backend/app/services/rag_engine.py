from openai import OpenAI
from backend.app.config import settings
from backend.app.database import vector_db

class RAGEngine:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate_answer(self, query: str, file_id: str) -> dict:
        """
        Finds relevant context in the database and uses OpenAI to generate 
        an answer with explicit timestamp or page source references.
        """
        # 1. Fetch relevant text chunks from our local Vector DB
        context_chunks = vector_db.query_similarity(query, file_id, n_results=3)
        
        # 2. Build context string and track metadata references
        context_text = ""
        sources = []
        
        for idx, chunk in enumerate(context_chunks):
            context_text += f"\n[Source {idx+1}]: {chunk['text']}\n"
            sources.append(chunk["metadata"])

        # Fallback for local testing without active OpenAI billing
        if settings.OPENAI_API_KEY == "mock-key-for-local-testing":
            return self._generate_mock_rag_response(query, sources)

        # 3. Construct system instructions forcing the model to cite its sources
        system_prompt = (
            "You are an expert AI Assistant answering questions based strictly on the provided context.\n"
            "CRITICAL RULE: When referencing information from a source, you MUST cite it using the exact "
            "timestamp format '[MM:SS]' if it is a media file, or '[Page X]' if it is a PDF file.\n"
            f"Context details:\n{context_text}"
        )

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.3
        )

        return {
            "answer": response.choices[0].message.content,
            "sources": sources
        }

    def generate_summary(self, file_id: str) -> str:
        """
        Queries all contents of a specific file to generate a brief summary.
        """
        # Fetch up to 10 chunks to understand the overall content structure
        results = vector_db.collection.get(where={"file_id": file_id}, limit=10)
        combined_text = " ".join(results.get("documents", []))

        if not combined_text:
            return "No content found to summarize."

        if settings.OPENAI_API_KEY == "mock-key-for-local-testing":
            return f"This is a high-level mock summary of the uploaded document asset ({file_id}) focusing on system architecture."

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Provide a concise summary paragraph highlighting the main topics of this content."},
                {"role": "user", "content": combined_text}
            ],
            temperature=0.5
        )
        return response.choices[0].message.content

    def _generate_mock_rag_response(self, query: str, sources: list[dict]) -> dict:
        """
        Mock backup handler to ensure the app works beautifully offline or during testing.
        """
        # Determine source metadata presentation details
        source_citation = "[Page 1]"
        if sources and sources[0].get("source_type") == "media":
            start_time = sources[0].get("start_time", 0.0)
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            source_citation = f"[{minutes:02d}:{seconds:02d}]"

        return {
            "answer": f"Based on the documents, you asked: '{query}'. Here is the mock response pointing directly to the source reference at {source_citation}.",
            "sources": sources
        }
        