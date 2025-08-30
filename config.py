import os
from dotenv import load_dotenv
from constants import *

# Load environment variables
load_dotenv()

# SSL Certificate handling (if needed)
CERT_PATH = r"C:\Users\HP\combined-ca.pem"
if os.path.exists(CERT_PATH):
    os.environ['REQUESTS_CA_BUNDLE'] = CERT_PATH
    os.environ['SSL_CERT_FILE'] = CERT_PATH

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

# Dynamic URL Configuration - handles both local dev and production
APP_HOST = os.getenv("APP_HOST", DEFAULT_APP_HOST).strip()
REDIRECT_URI = os.getenv("REDIRECT_URI", DEFAULT_REDIRECT_URI).strip()

# Domain configuration
ALLOWED_DOMAIN = os.getenv("ALLOWED_DOMAIN", DEFAULT_ALLOWED_DOMAIN).strip()

# Authentication
COOKIE_SECRET = os.getenv("COOKIE_SECRET", "").strip()
COOKIE_NAME = os.getenv("COOKIE_NAME", DEFAULT_COOKIE_NAME).strip()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# RAG Configuration
RAG_DOCUMENTS_PATH = os.getenv("RAG_DOCUMENTS_PATH", DEFAULT_RAG_DOCUMENTS_PATH).strip()
RAG_INDEX_PATH = os.getenv("RAG_INDEX_PATH", DEFAULT_RAG_INDEX_PATH).strip()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL).strip()
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", str(DEFAULT_CHUNK_SIZE)))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", str(DEFAULT_CHUNK_OVERLAP)))
TOP_K = int(os.getenv("TOP_K", str(DEFAULT_TOP_K)))

# Chat Configuration
CHAT_MODEL = os.getenv("CHAT_MODEL", DEFAULT_CHAT_MODEL).strip()
TEMPERATURE = float(os.getenv("TEMPERATURE", str(DEFAULT_TEMPERATURE)))

# Validation
required_vars = {
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_KEY": SUPABASE_KEY,
    "SUPABASE_SERVICE_ROLE_KEY": SUPABASE_SERVICE_ROLE_KEY,
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "COOKIE_SECRET": COOKIE_SECRET
}

for var_name, var_value in required_vars.items():
    if not var_value:
        raise ValueError(f"{var_name} must be set in .env file or environment variables")

# Create directories
os.makedirs(RAG_DOCUMENTS_PATH, exist_ok=True)
os.makedirs(RAG_INDEX_PATH, exist_ok=True)

# Environment detection for logging
is_production = "localhost" not in APP_HOST.lower()
environment = "production" if is_production else "development"

print(f"🤖 Sevabot Configuration Loaded ({environment}):")
print(f"   🌐 App Host: {APP_HOST}")
print(f"   🔄 Redirect URI: {REDIRECT_URI}")
print(f"   📚 Documents Path: {RAG_DOCUMENTS_PATH}")
print(f"   📊 Chunk Size: {CHUNK_SIZE}, Overlap: {CHUNK_OVERLAP}")
print(f"   🔍 Top K Retrieval: {TOP_K}")
print(f"   🧠 Model: {CHAT_MODEL}, Temperature: {TEMPERATURE}")
print(f"   👥 Max Sessions: {MAX_SESSIONS_PER_USER}, Max History: {MAX_HISTORY_TURNS}")
print(f"   📧 Allowed Domain: {ALLOWED_DOMAIN}")
print(f"   🔧 Ready for multi-user operation")