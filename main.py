# main.py - FastAPI application entry point
import warnings
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import RedirectResponse
import uvicorn

# Suppress warnings early
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="langchain")

# Import modules
try:
    from auth import router as auth_router
    print(f"✅ Auth router imported with {len(auth_router.routes)} routes")
except Exception as e:
    print(f"❌ Error importing auth router: {e}")
    exit(1)

from ui import create_ui
from file_service import file_service
from rag_service import rag_service
from chat_service import chat_service

# API router for health checks and basic endpoints
api_router = APIRouter(tags=["API"])

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Sevabot RAG Assistant",
        "version": "2.0.0"
    }

@api_router.get("/api/user-stats/{user_email}")
async def get_user_stats(user_email: str):
    """Get user statistics"""
    try:
        conversations = chat_service.get_user_conversations(user_email)
        files = file_service.list_user_files(user_email)
        doc_count = rag_service.get_user_document_count(user_email)
        
        return {
            "conversations_count": len(conversations),
            "files_count": len(files),
            "indexed_chunks": doc_count,
            "user_email": user_email
        }
    except Exception as e:
        return {"error": str(e)}

# FastAPI app
app = FastAPI(
    title="Sevabot RAG Assistant",
    description="Multi-user RAG system with file management and conversational chat",
    version="2.0.0",
    docs_url="/admin/docs",
    redoc_url="/admin/redoc",
    openapi_url="/admin/openapi.json"
)

# Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure for production
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, tags=["Authentication"])
app.include_router(api_router)

# Create UI
create_ui(app)

# Root redirect
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/chat")

@app.on_event("startup")
async def startup_event():
    print("🚀 Starting Sevabot RAG Assistant...")
    print("✅ Multi-user file management ready")
    print("✅ ChromaDB vector stores initialized")
    print("✅ Conversation management ready")
    print("✅ Authentication system ready")
    print("🌐 Application ready for traffic")

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Shutting down Sevabot RAG Assistant...")
    # Cleanup if needed
    print("✅ Shutdown complete")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        workers=1,
        reload=False,
        access_log=True,
        log_level="info"
    )