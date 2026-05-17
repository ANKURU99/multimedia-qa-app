import chromadb
from chromadb.config import Settings as ChromaSettings
from backend.app.config import settings

class VectorDatabase:
    def __init__(self):
        # Initialize a persistent local Chroma client that saves files to disk
        self.client = chromadb.PersistentClient(
            path=settings.VECTOR_DB_DIR,
            settings=ChromaSettings(allow_reset=True)
        )
        # Create or fetch our single collection for multimedia assets
        self.collection = self.client.get_or_create_collection(
            name="multimedia_knowledge_base"
        )

    def add_documents(self, chunks: list[dict], file_id: str):
        """
        Takes processed chunks from our PDF/Media workers and saves them to ChromaDB.
        """
        documents = []
        metadatas = []
        ids = []

        for idx, chunk in enumerate(chunks):
            documents.append(chunk["text"])
            
            # Combine individual chunk metadata with a tracking file_id
            meta = chunk["metadata"].copy()
            meta["file_id"] = file_id
            metadatas.append(meta)
            
            ids.append(f"{file_id}_{idx}")

        if documents:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

    def query_similarity(self, query_text: str, file_id: str, n_results: int = 3) -> list[dict]:
        """
        Searches the database for chunks that match the query text, filtered by file_id.
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where={"file_id": file_id}
        )

        formatted_results = []
        if results and results["documents"] and results["documents"][0]:
            for idx in range(len(results["documents"][0])):
                formatted_results.append({
                    "text": results["documents"][0][idx],
                    "metadata": results["metadatas"][0][idx]
                })
        return formatted_results

# Global singleton instance
vector_db = VectorDatabase()
