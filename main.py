# main.py - FastAPI application with RAG endpoints
import warnings
import os
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

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
from chat_service import chat_service

# Import enhanced RAG service with router
try:
    from rag_service import rag_service, router as rag_router
    print(f"✅ RAG service and router imported")
except Exception as e:
    print(f"❌ Error importing RAG service: {e}")
    exit(1)

# API router for health checks and basic endpoints
api_router = APIRouter(tags=["API"])


@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "SEVABOT RAG Assistant",
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
    title="SEVABOT RAG Assistant",
    description="Multi-user RAG system with document management and conversational chat",
    version="2.0.0",
    docs_url="/admin/docs",
    redoc_url="/admin/redoc",
    openapi_url="/admin/openapi.json"
)

# Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Mount common knowledge files as static
common_docs_path = os.getenv("COMMON_KNOWLEDGE_PATH", "/app/common_knowledge")
app.mount(
    "/docs",
    StaticFiles(directory=common_docs_path),
    name="docs"
)

# Include routers
app.include_router(auth_router, tags=["Authentication"])
app.include_router(api_router)
app.include_router(rag_router, tags=["RAG"])

# Create UI
create_ui(app)

# Root redirect
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/chat")


@app.on_event("startup")
async def startup_event():
    print("🚀 Starting SEVABOT RAG Assistant...")
    print("✅ Multi-user file management ready")
    print("✅ ChromaDB vector stores initialized")
    print("✅ Conversation management ready")
    print("✅ Authentication system ready")
    print("✅ Vector database cleanup endpoints ready")
    print("🌐 Application ready for traffic")


@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Shutting down SEVABOT RAG Assistant...")
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