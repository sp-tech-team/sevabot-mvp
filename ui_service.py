# ui_service.py - Core UI service with fixes
import threading
from typing import List, Dict, Optional, Tuple, Any
import gradio as gr
from constants import MAX_SESSIONS_PER_USER, ERROR_MESSAGES, USER_ROLES
from chat_service import chat_service
from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, IS_PRODUCTION
from supabase import create_client

class UIService:
    """Core UI service"""
    
    def __init__(self):
        self.current_user = {"email": "", "name": "User", "user_id": "", "role": "user"}
        self.current_conversation_id = None
        self.last_assistant_message_id = None
        self._lock = threading.Lock()
    
    def set_user(self, user_data: Dict):
        """Set current user with role"""
        with self._lock:
            self.current_user = {
                "email": user_data.get("email", ""),
                "name": user_data.get("name", "User"),
                "user_id": user_data.get("user_id", ""),
                "role": user_data.get("role", "user")
            }
    
    def get_display_name(self) -> str:
        """Get user's display name"""
        name = self.current_user.get("name", "")
        email = self.current_user.get("email", "")
        
        if name and name != "User":
            return name.split()[0]
        
        if email:
            email_name = email.split("@")[0]
            return email_name.replace(".", " ").title().split()[0]
        
        return "Friend"
    
    def is_logged_in(self) -> bool:
        return bool(self.current_user.get("email"))
    
    def is_admin(self) -> bool:
        return self.current_user.get("role") == USER_ROLES['admin']
    
    def is_spoc(self) -> bool:
        return self.current_user.get("role") == USER_ROLES['spoc']
    
    def is_admin_or_spoc(self) -> bool:
        return self.is_admin() or self.is_spoc()
    
    def get_user_role(self) -> str:
        return self.current_user.get("role", "user")
    
    def get_last_assistant_message_id(self) -> Optional[str]:
        return self.last_assistant_message_id
    
    def submit_feedback(self, message_id: str, feedback: str) -> bool:
        try:
            return chat_service.update_message_feedback(message_id, feedback)
        except Exception as e:
            print(f"Error submitting feedback: {e}")
            return False
    
    def load_initial_data(self) -> Tuple[str, gr.update]:
        """Load initial data for UI"""
        conversations = chat_service.get_user_conversations(self.current_user["email"])
        session_choices = [(conv["title"], conv["id"]) for conv in conversations]
        return "", gr.update(choices=session_choices, value=None)
    
    def get_initial_visibility(self):
        """Get tab visibility based on user role"""
        user_role = self.get_user_role()
        user_email = self.current_user.get("email", "")
        
        if user_role == "admin":
            greeting = f"Namaskaram {self.get_display_name()}! [ADMIN]"
        elif user_role == "spoc":
            greeting = f"Namaskaram {self.get_display_name()}! [SPOC]"
        else:
            greeting = f"Namaskaram {self.get_display_name()}!"
        
        sessions_update = self.load_initial_data()[1]
        
        # Tab visibility
        files_tab_visible = True #user_role == "user"
        file_manager_common_visible = user_role in ["admin", "spoc"]
        file_manager_users_visible = user_role == "admin"  # Only admin
        users_tab_visible = user_role == "admin"
        
        # Section visibility within tabs
        admin_chat_section_visible = user_role in ["admin", "spoc"]
        admin_upload_section_visible = user_role == "admin"
        reindex_visible = user_role == "admin"
        cleanup_visible = user_role == "admin"
        
        # Auto-select current user for admin/SPOC chat view
        default_chat_user = user_email if user_role in ["admin", "spoc"] else None
        
        # Title and styling
        if user_role == "spoc":
            title_text = "## SPOC File Management"
            container_class = "spoc-section"
        else:
            title_text = "## Common Knowledge Repository"
            container_class = "admin-section"
        
        guidelines_text = """
        **Common Knowledge Repository:**
        Max file size: 10MB | Formats: .txt, .md, .pdf, .docx | PDFs must be text-extractable
        """
        
        return (
            greeting,
            sessions_update,
            gr.update(visible=files_tab_visible),
            gr.update(visible=file_manager_common_visible),
            gr.update(visible=file_manager_users_visible),
            gr.update(visible=users_tab_visible),
            gr.update(visible=admin_chat_section_visible),
            gr.update(visible=admin_upload_section_visible),
            gr.update(visible=reindex_visible),
            gr.update(visible=cleanup_visible),
            gr.update(value=title_text),
            gr.update(value=guidelines_text),
            gr.update(elem_classes=container_class),
            gr.update(value=default_chat_user)
        )
    
    def send_message(self, message: str, history: List[List[str]], conversation_id: Optional[str]) -> Tuple[List[List[str]], str, Optional[str], gr.update, str]:
        """Send message and get response"""
        if not message.strip():
            return history or [], "", conversation_id, gr.update(), ""
        
        if not self.is_logged_in():
            return (history or []) + [[message, "Please log in to continue"]], "", conversation_id, gr.update(), ""
        
        try:
            # Create new conversation if needed
            if not conversation_id:
                existing_conversations = chat_service.get_user_conversations(self.current_user["email"])
                if len(existing_conversations) >= MAX_SESSIONS_PER_USER:
                    return (history or []) + [[message, ERROR_MESSAGES["session_limit"]]], "", conversation_id, gr.update(), ERROR_MESSAGES["session_limit"]
                
                title = chat_service.generate_title(message)
                conversation_id = chat_service.create_conversation(self.current_user["email"], title)
                
                if not conversation_id:
                    return (history or []) + [[message, "Error creating conversation"]], "", conversation_id, gr.update(), "Error creating conversation"
                
                self.current_conversation_id = conversation_id
            
            # Store user message
            chat_service.store_message(conversation_id, "user", message)
            
            # Get conversation history for context
            conv_history = chat_service.get_conversation_history(conversation_id)
            
            # Generate response using common knowledge repository
            response = chat_service.create_rag_response(message, conv_history)
            
            # Store assistant message
            assistant_msg_id = chat_service.store_message(conversation_id, "assistant", response)
            self.last_assistant_message_id = assistant_msg_id
            
            # Update conversation timestamp
            chat_service.update_conversation_timestamp(conversation_id)
            
            # Update history and sessions
            new_history = (history or []) + [[message, response]]
            conversations = chat_service.get_user_conversations(self.current_user["email"])
            session_choices = [(conv["title"], conv["id"]) for conv in conversations]
            sessions_update = gr.update(choices=session_choices, value=conversation_id)
            
            return new_history, "", conversation_id, sessions_update, ""
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            return (history or []) + [[message, error_msg]], "", conversation_id, gr.update(), error_msg
    
    def load_conversation(self, conversation_id: Optional[str]) -> Tuple[List[List[str]], Optional[str], str]:
        """Load conversation history with feedback"""
        if not conversation_id:
            return [], None, ""
        
        try:
            self.current_conversation_id = conversation_id
            
            # Get messages with feedback from database
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            
            result = supabase.table("messages")\
                .select("*")\
                .eq("conversation_id", conversation_id)\
                .order("created_at")\
                .execute()
            
            if not result.data:
                return [], conversation_id, "Empty conversation loaded"
            
            # Create proper message format for Gradio
            gradio_history = []
            user_msg = None
            
            for msg in result.data:
                if msg["role"] == "user":
                    user_msg = msg["content"]
                elif msg["role"] == "assistant" and user_msg:
                    assistant_content = msg["content"]
                    
                    # Add feedback if exists
                    if msg.get("feedback"):
                        feedback_data = str(msg["feedback"]).strip()
                        if feedback_data and feedback_data != "None":
                            if ":" in feedback_data:
                                feedback_parts = feedback_data.split(":", 1)
                                feedback_type = feedback_parts[0].strip().lower()
                                remarks = feedback_parts[1].strip() if len(feedback_parts) > 1 else ""
                            else:
                                feedback_type = feedback_data.lower()
                                remarks = ""
                            
                            feedback_emoji = {"fully": "✅", "partially": "⚠️", "nopes": "❌"}
                            emoji = feedback_emoji.get(feedback_type, "")
                            feedback_display = f"{emoji} {feedback_type.title()}"
                            
                            if remarks:
                                feedback_display += f" - {remarks}"
                            
                            assistant_content += f"\n\n*[Feedback: {feedback_display}]*"
                    
                    gradio_history.append([user_msg, assistant_content])
                    user_msg = None
            
            return gradio_history, conversation_id, f"Loaded conversation with {len(gradio_history)} messages"
            
        except Exception as e:
            print(f"Error loading conversation: {e}")
            history = chat_service.get_conversation_history(conversation_id)
            gradio_history = [[user_msg, assistant_msg] for user_msg, assistant_msg in history]
            return gradio_history, conversation_id, f"Loaded conversation (feedback unavailable)"
    
    def create_new_chat(self) -> Tuple[List[List[str]], Optional[str], gr.update, str]:
        """Create new chat with greeting"""
        existing_conversations = chat_service.get_user_conversations(self.current_user["email"])
        if len(existing_conversations) >= MAX_SESSIONS_PER_USER:
            return [], None, gr.update(), ERROR_MESSAGES["session_limit"]
        
        self.current_conversation_id = None
        
        user_name = self.get_display_name()
        greeting = f"Namaskaram {user_name}! Ready to explore the knowledge repository?"
        initial_history = [["", greeting]]
        
        conversations = chat_service.get_user_conversations(self.current_user["email"])
        session_choices = [(conv["title"], conv["id"]) for conv in conversations]
        sessions_update = gr.update(choices=session_choices, value=None)
        
        return initial_history, None, sessions_update, "New chat ready"
    
    def delete_conversation(self, conversation_id: Optional[str]) -> Tuple[List[List[str]], Optional[str], gr.update, str]:
        """Delete conversation"""
        if not conversation_id:
            return [], None, gr.update(), "No conversation selected"
        
        try:
            # For non-admins, only allow deleting own conversations
            if not self.is_admin():
                supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
                conv_result = supabase.table("conversations")\
                    .select("user_id")\
                    .eq("id", conversation_id)\
                    .execute()
                
                if not conv_result.data or conv_result.data[0]["user_id"] != self.current_user["email"]:
                    return [], conversation_id, gr.update(), "Can only delete your own conversations"
            
            success = chat_service.delete_conversation(conversation_id, self.current_user["email"])
            
            if success:
                if self.current_conversation_id == conversation_id:
                    self.current_conversation_id = None
                
                conversations = chat_service.get_user_conversations(self.current_user["email"])
                session_choices = [(conv["title"], conv["id"]) for conv in conversations]
                sessions_update = gr.update(choices=session_choices, value=None)
                
                return [], None, sessions_update, "Conversation deleted"
            else:
                return [], conversation_id, gr.update(), "Failed to delete conversation"
                
        except Exception as e:
            return [], conversation_id, gr.update(), f"Error: {str(e)}"

# Global UI service instance
ui_service = UIService()