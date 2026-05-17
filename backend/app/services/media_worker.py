import os
from openai import OpenAI
from backend.app.config import settings

class MediaWorker:
    def __init__(self):
        # Initializes the OpenAI client using the key from config
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def transcribe_with_timestamps(self, file_path: str) -> list[dict]:
        """
        Sends an audio/video file to OpenAI Whisper API and requests verbose 
        segment-level outputs to capture precise start and end timestamps.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Media file not found at: {file_path}")

        # Fallback to mock behavior if we are running local tests without a real API key
        if settings.OPENAI_API_KEY == "mock-key-for-local-testing":
            return self._generate_mock_transcript(file_path)

        with open(file_path, "rb") as audio_file:
            # We request 'verbose_json' format to get segment-by-segment timestamps
            transcript_response = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json"
            )

        chunks = []
        # Safely loop through transcription segments
        segments = getattr(transcript_response, 'segments', [])
        for segment in segments:
            chunks.append({
                "text": segment.get("text", "").strip(),
                "metadata": {
                    "source_type": "media",
                    "start_time": round(segment.get("start", 0.0), 2),
                    "end_time": round(segment.get("end", 0.0), 2),
                    "file_path": file_path
                }
            })
            
        return chunks

    def _generate_mock_transcript(self, file_path: str) -> list[dict]:
        """
        Helper mock method to ensure your backend runs perfectly during local testing
        without consuming real OpenAI credits.
        """
        filename = os.path.basename(file_path)
        return [
            {
                "text": f"Welcome to the overview of the uploaded file named {filename}.",
                "metadata": {"source_type": "media", "start_time": 0.0, "end_time": 4.5, "file_path": file_path}
            },
            {
                "text": "In this section, we cover the primary data structures and foundational setups.",
                "metadata": {"source_type": "media", "start_time": 4.6, "end_time": 12.3, "file_path": file_path}
            },
            {
                "text": "Finally, the system runs an automated testing matrix ensuring code stability.",
                "metadata": {"source_type": "media", "start_time": 12.4, "end_time": 20.0, "file_path": file_path}
            }
        ]
        