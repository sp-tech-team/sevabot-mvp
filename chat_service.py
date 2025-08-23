# chat_service.py - Clean chat service with enhanced citation
import warnings
from datetime import datetime
from typing import List, Dict, Optional, Tuple

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="langchain")

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from config import (
    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, 
    OPENAI_API_KEY, CHAT_MODEL, TEMPERATURE, TOP_K
)
from constants import (
    SYSTEM_PROMPT, MAX_HISTORY_TURNS, MAX_SESSIONS_PER_USER,
    ERROR_MESSAGES
)
from supabase import create_client
from rag_service import rag_service

class ChatService:
    """Manages chat conversations and RAG responses"""
    
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        
        # Initialize chat model
        self.chat_model = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model=CHAT_MODEL,
            temperature=TEMPERATURE
        )
    
    def create_conversation(self, user_email: str, title: str) -> Optional[str]:
        """Create new conversation"""
        try:
            sessions = self.get_user_conversations(user_email)
            if len(sessions) >= MAX_SESSIONS_PER_USER:
                return None
            
            conv_data = {
                "user_id": user_email,
                "title": title,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table("conversations").insert(conv_data).execute()
            
            if result.data:
                return result.data[0]["id"]
            return None
            
        except Exception as e:
            print(f"Error creating conversation: {e}")
            return None
    
    def get_user_conversations(self, user_email: str) -> List[Dict]:
        """Get user conversations ordered by most recent"""
        try:
            result = self.supabase.table("conversations")\
                .select("*")\
                .eq("user_id", user_email)\
                .order("updated_at", desc=True)\
                .limit(MAX_SESSIONS_PER_USER)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error getting conversations: {e}")
            return []
    
    def delete_conversation(self, conversation_id: str, user_email: str) -> bool:
        """Delete conversation and all its messages"""
        try:
            self.supabase.table("messages")\
                .delete()\
                .eq("conversation_id", conversation_id)\
                .execute()
            
            result = self.supabase.table("conversations")\
                .delete()\
                .eq("id", conversation_id)\
                .eq("user_id", user_email)\
                .execute()
            
            return True
            
        except Exception as e:
            print(f"Error deleting conversation: {e}")
            return False
    
    def get_conversation_history(self, conversation_id: str) -> List[Tuple[str, str]]:
        """Get conversation history as list of (user_msg, assistant_msg) tuples"""
        try:
            result = self.supabase.table("messages")\
                .select("*")\
                .eq("conversation_id", conversation_id)\
                .order("created_at")\
                .execute()
            
            if not result.data:
                return []
            
            history = []
            user_msg = None
            
            for msg in result.data:
                if msg["role"] == "user":
                    user_msg = msg["content"]
                elif msg["role"] == "assistant" and user_msg:
                    history.append((user_msg, msg["content"]))
                    user_msg = None
            
            return history
            
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return []
    
    def store_message(self, conversation_id: str, role: str, content: str) -> Optional[str]:
        """Store message and return message ID"""
        try:
            msg_data = {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table("messages").insert(msg_data).execute()
            
            if result.data:
                return result.data[0]["id"]
            return None
            
        except Exception as e:
            print(f"Error storing message: {e}")
            return None
    
    def update_conversation_timestamp(self, conversation_id: str):
        """Update conversation's updated_at timestamp"""
        try:
            self.supabase.table("conversations")\
                .update({"updated_at": datetime.utcnow().isoformat()})\
                .eq("id", conversation_id)\
                .execute()
        except Exception as e:
            print(f"Error updating conversation timestamp: {e}")
    
    def generate_title(self, message: str) -> str:
        """Generate conversation title from first message"""
        if not message or len(message.strip()) < 5:
            return "New Chat"
        
        try:
            title_model = ChatOpenAI(
                api_key=OPENAI_API_KEY,
                model="gpt-4o-mini",
                temperature=0.3
            )
            
            system_msg = SystemMessage(content="Generate a concise 2-4 word title for this conversation. Focus on the main topic. Examples: 'Document Analysis', 'Project Planning', 'Research Query'. No quotes or punctuation.")
            human_msg = HumanMessage(content=f"Create a title for: {message[:100]}")
            
            response = title_model.invoke([system_msg, human_msg])
            
            title = response.content.strip()
            import re
            title = re.sub(r'[^\w\s]', '', title)
            words = title.split()[:4]
            
            if len(words) >= 2:
                return ' '.join(words).title()
            
        except Exception as e:
            print(f"Error generating title: {e}")
        
        words = message.split()[:3]
        return ' '.join(words).title() if words else "New Chat"
    
    def create_rag_response(self, user_email: str, query: str, conversation_history: List[Tuple[str, str]]) -> str:
        """Create RAG response with enhanced source citation"""
        try:
            search_results = rag_service.search_user_documents(user_email, query, TOP_K)
            
            if not search_results:
                return self._no_documents_response()
            
            # Prepare context with CLEAR DOCUMENT NAMES for citation
            context_parts = []
            document_names = []
            
            for chunk, source, similarity, metadata in search_results:
                document_name = source if source != 'Unknown' else metadata.get('file_name', 'Unknown Document')
                context_part = f"[Document: {document_name}]\n{chunk}"
                context_parts.append(context_part)
                if document_name not in document_names:
                    document_names.append(document_name)
            
            full_context = "\n\n".join(context_parts)
            
            # Prepare conversation context
            recent_history = conversation_history[-MAX_HISTORY_TURNS:] if conversation_history else []
            history_context = ""
            
            if recent_history:
                history_parts = []
                for user_msg, assistant_msg in recent_history:
                    history_parts.append(f"User: {user_msg}")
                    history_parts.append(f"Assistant: {assistant_msg}")
                history_context = "\n".join(history_parts)
            
            # Enhanced system message with stronger citation requirements
            system_content = f"""{SYSTEM_PROMPT}

CONVERSATION HISTORY:
{history_context}

AVAILABLE DOCUMENTS FOR CITATION: {', '.join(document_names)}

CONTEXT FROM DOCUMENTS:
{full_context}

REMEMBER: You MUST start your response with source citations like "Based on [Document Name] and [Document Name]..." and continue citing sources throughout your response."""
            
            # Generate response
            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=query)
            ]
            
            response = self.chat_model.invoke(messages)
            
            # Clean up response
            clean_response = response.content.replace('|', '').replace('```', '').strip()
            import re
            clean_response = re.sub(r'\|.*?\|', '', clean_response)
            clean_response = re.sub(r'-+\|', '', clean_response)
            clean_response = re.sub(r'\n\s*\n', '\n\n', clean_response).strip()
            
            return clean_response
            
        except Exception as e:
            print(f"Error creating RAG response: {e}")
            return ERROR_MESSAGES["embedding_error"]
    
    def _no_documents_response(self) -> str:
        """Response when no documents are available"""
        return ERROR_MESSAGES["no_documents"]
    
    def update_message_feedback(self, message_id: str, feedback: str) -> bool:
        """Update message feedback"""
        try:
            self.supabase.table("messages")\
                .update({"feedback": feedback})\
                .eq("id", message_id)\
                .execute()
            
            return True
            
        except Exception as e:
            print(f"Error updating message feedback: {e}")
            return False

# Global chat service instance
chat_service = ChatService()