import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import init_db
from backend.api import endpoints

# Initialize FastAPI application
app = FastAPI(
    title="AI Contract Analyzer API",
    description="Backend services for parsing, chunking, indexing, and auditing contract PDFs with Gemini.",
    version="1.0.0"
)

# Set up CORS middleware to allow requests from frontend app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database on startup
@app.on_event("startup")
def startup_event():
    init_db()

# Include API endpoints
app.include_router(endpoints.router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "app": "AI Contract Analyzer API",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.app:app", host="0.0.0.0", port=port, reload=True)
