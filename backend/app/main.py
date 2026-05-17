import numpy as np
np.float_ = np.float64  # Manually inject the alias NumPy 2.0 removed

# ... (rest of your original main.py code continues here)
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.routes import upload, chat  # Import our new route files

# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION
)

# Configure CORS so your React frontend running on another port can talk to it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure our local file upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Register our sub-routers to open the HTTP endpoints
app.include_router(upload.router)
app.include_router(chat.router)

@app.get("/")
async def root():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION
    }
