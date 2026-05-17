from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "Multimedia Q&A API"
    VERSION: str = "1.0.0"
    
    # API Keys (Will look for these in environment variables)
    OPENAI_API_KEY: str = "mock-key-for-local-testing"
    
    # Storage Paths
    UPLOAD_DIR: str = "uploads"
    VECTOR_DB_DIR: str = "chroma_db"

    class Config:
        env_file = ".env"

settings = Settings()
