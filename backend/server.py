"""FastAPI HTTP server runner for GeCompose."""
from __future__ import annotations
import uvicorn
from backend.http.app import app

if __name__ == "__main__":
    uvicorn.run("backend.http.app:app", host="127.0.0.1", port=8000, reload=False)
