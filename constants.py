# constants.py - Application Constants

# App Configuration - Development defaults (will be overridden by environment variables in production)
DEFAULT_REDIRECT_URI = "http://localhost:8001/auth/callback"
DEFAULT_APP_HOST = "http://localhost:8001"
DEFAULT_ALLOWED_DOMAIN = "sadhguru.org"
DEFAULT_COOKIE_NAME = "sevabot_session"

# RAG Configuration
DEFAULT_RAG_DOCUMENTS_PATH = "./user_documents"
DEFAULT_RAG_INDEX_PATH = "./rag_index"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_TOP_K = 8  # Increased from 5 to 8 for better context coverage

# Chat Configuration
DEFAULT_CHAT_MODEL = "gpt-4o"  # Using GPT-4o for better reasoning
DEFAULT_TEMPERATURE = 0.7
MAX_HISTORY_TURNS = 10  # Maximum conversation turns to keep in context
MAX_SESSIONS_PER_USER = 10  # Maximum sessions per user

# Session Configuration
SESSION_MAX_AGE = 86400  # 24 hours
SESSION_SALT = "sevabot-auth"

# File Configuration
SUPPORTED_EXTENSIONS = ['.txt', '.md', '.pdf', '.docx']
MAX_FILE_SIZE_MB = 10

NAMASKARAM_GREETINGS = [
    "Namaskaram! Ready to dive into your digital dharma library?",
    "Namaskaram! Let's explore what wisdom your documents hold today!",
    "Namaskaram! Your seva companion is here - what shall we discover?",
    "Namaskaram! Time to unlock some knowledge karma from your files!",
    "Namaskaram! I'm here for your document darshan - ask away!",
    "Namaskaram! Let's turn your PDFs into prasadam of wisdom!",
    "Namaskaram! Ready for some digital satsang with your documents?",
    "Namaskaram! Your friendly document guru is at your seva!",
    "Namaskaram! What treasures shall we find in your knowledge vault today?",
    "Namaskaram! Time for some enlightening document exploration together!"
]

# System Prompt
SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions based ONLY on the provided context from uploaded documents.

CRITICAL CITATION REQUIREMENTS:
1. START EVERY RESPONSE by citing the relevant sources: "Based on [Document Name] and [Document Name]..."
2. Answer questions ONLY using information from the provided context
3. If the context doesn't contain enough information to answer the question, clearly state "I don't have enough information in the available documents to answer this question"
4. Do NOT make up information or use general knowledge beyond what's in the context
5. Be accurate and stick to the facts provided in the context
6. ALWAYS cite sources throughout your response using formats like:
   - "According to [Document Name], ..."
   - "As mentioned in [Document Name], ..."
   - "The [Document Name] states that..."
7. If you're uncertain about any details, mention your uncertainty but still cite the source
8. Provide helpful, clear answers when the information is available in the context

RESPONSE FORMAT:
- Start with: "Based on [Document Name(s)], ..." 
- Continue with source citations throughout
- End with confidence level if uncertain

RESPONSE STYLE:
- Use humble and volunteering language naturally in your responses
- Be respectful and warm in your tone
- Show willingness to help and serve
- Use phrases like "I'm happy to help", "Let me assist you", "In service to your learning"
- Express gratitude when appropriate

MANDATORY CITATION EXAMPLES:
- "Based on the Employee Handbook, vacation days must be requested 2 weeks in advance."
- "According to the Technical Specifications document and the User Manual, the system requires 8GB RAM."
- "The Marketing Report indicates that sales increased by 15% last quarter."
- "As mentioned in both the Budget Report and Financial Summary, expenses exceeded projections."

Remember: ALWAYS start with source citation and maintain citations throughout. It's better to humbly say "I don't know" than to provide inaccurate information."""

# Error Messages
ERROR_MESSAGES = {
    "no_documents": "I don't have any documents uploaded to search through yet. I'd be happy to help once you upload some documents!",
    "embedding_error": "I encountered an error while processing your question. Please try again, and I'll do my best to help.",
    "no_openai_key": "OpenAI API key not configured. Please contact the administrator.",
    "file_too_large": f"File is too large. Maximum size is {MAX_FILE_SIZE_MB}MB.",
    "unsupported_format": f"Unsupported file format. Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}",
    "upload_error": "Error uploading file. Please try again.",
    "delete_error": "Error deleting file. Please try again.",
    "session_limit": f"You have reached the maximum limit of {MAX_SESSIONS_PER_USER} sessions. Please delete a session before creating a new one."
}