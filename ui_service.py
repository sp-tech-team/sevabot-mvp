# ui_service.py - Enhanced UI service with comprehensive functionality
import threading
from typing import List, Dict, Optional, Tuple, Any
import gradio as gr
from constants import MAX_SESSIONS_PER_USER, ERROR_MESSAGES, USER_ROLES
from chat_service import chat_service
from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, IS_PRODUCTION
from supabase import create_client

class EnhancedUIService:
    """Enhanced UI service with comprehensive file and vector operations"""
    
    def __init__(self):
        self.current_user = {"email": "", "name": "User", "user_id": "", "role": "user"}
        self.current_conversation_id = None
        self.last_assistant_message_id = None
        self._lock = threading.Lock()
    
    # ========== USER MANAGEMENT ==========
    
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
    
    # ========== INITIAL SETUP ==========
    
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
        
        # Tab visibility - Files tab visible for all users
        files_tab_visible = True
        file_manager_common_visible = user_role in ["admin", "spoc"]
        file_manager_users_visible = user_role == "admin"
        users_tab_visible = user_role == "admin"
        
        # Section visibility within tabs
        admin_chat_section_visible = user_role in ["admin", "spoc"]
        admin_upload_section_visible = user_role == "admin"
        reindex_visible = user_role == "admin"
        cleanup_visible = user_role == "admin"
        
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
            gr.update(value=None)
        )
    
    def load_initial_data(self) -> Tuple[str, gr.update]:
        """Load initial data for UI"""
        conversations = chat_service.get_user_conversations(self.current_user["email"])
        session_choices = [(conv["title"], conv["id"]) for conv in conversations]
        return "", gr.update(choices=session_choices, value=None)
    
    # ========== CHAT OPERATIONS ==========
    
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
            user_msg = {"role": "user", "content": message}
            assistant_msg = {"role": "assistant", "content": response}
            new_history = (history or []) + [[message, response]]
            conversations = chat_service.get_user_conversations(self.current_user["email"])
            session_choices = [(conv["title"], conv["id"]) for conv in conversations]
            sessions_update = gr.update(choices=session_choices, value=conversation_id)
            
            return new_history, "", conversation_id, sessions_update, ""
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            user_msg = {"role": "user", "content": message}
            assistant_msg = {"role": "assistant", "content": error_msg}
            return (history or []) + [user_msg, assistant_msg], "", conversation_id, gr.update(), error_msg

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
                    
                    gradio_history.extend([
                        {"role": "user", "content": user_msg},
                        {"role": "assistant", "content": assistant_content}
                    ])
                    user_msg = None
            
            return gradio_history, conversation_id, f"Loaded conversation with {len(gradio_history)//2} messages"
            
        except Exception as e:
            print(f"Error loading conversation: {e}")
            history = chat_service.get_conversation_history(conversation_id)
            gradio_history = []
            for user_msg, assistant_msg in history:
                gradio_history.extend([
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": assistant_msg}
                ])
            return gradio_history, conversation_id, f"Loaded conversation (feedback unavailable)"

    def create_new_chat(self) -> Tuple[List[List[str]], Optional[str], gr.update, str]:
        """Create new chat with greeting"""
        existing_conversations = chat_service.get_user_conversations(self.current_user["email"])
        if len(existing_conversations) >= MAX_SESSIONS_PER_USER:
            return [], None, gr.update(), ERROR_MESSAGES["session_limit"]
        
        self.current_conversation_id = None
        
        user_name = self.get_display_name()
        greeting = f"Namaskaram {user_name}! Ready to explore the knowledge repository?"
        initial_history = [{"role": "assistant", "content": greeting}]
        
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
    
    def submit_feedback(self, message_id: str, feedback: str) -> bool:
        """Submit feedback for a message"""
        try:
            return chat_service.update_message_feedback(message_id, feedback)
        except Exception as e:
            print(f"Error submitting feedback: {e}")
            return False
    
    # ========== FILE OPERATIONS ==========
    
    def _filter_file_columns(self, files: List[List[Any]], is_personal: bool = False) -> List[List[Any]]:
        """Filter file data - keep all columns for personal files now"""
        try:
            filtered_files = []
            for file_row in files:
                if len(file_row) >= 7:
                    # For both common and personal: [Name, Size, Type, Uploaded, Source] (remove chunks[3], status[4])
                    filtered_row = [file_row[0], file_row[1], file_row[2], file_row[5], file_row[6]]
                    filtered_files.append(filtered_row)
            return filtered_files
        except Exception as e:
            print(f"Error filtering file columns: {e}")
            return []
    
    def get_common_files_for_display(self, search_term: str = "") -> List[List[Any]]:
        """Get common knowledge files for Files tab display"""
        try:
            from file_services import enhanced_file_service
            files = enhanced_file_service.get_common_knowledge_file_list(search_term)
            return self._filter_file_columns(files, is_personal=False)
        except Exception as e:
            print(f"Error getting common files for display: {e}")
            return []

    def get_personal_files_for_display(self, search_term: str = "") -> List[List[Any]]:
        """Get personal files for current user"""
        try:
            from file_services import enhanced_file_service
            user_email = self.current_user.get("email", "")
            if not user_email:
                return []
            
            files = enhanced_file_service.get_user_file_list(user_email, search_term)
            return self._filter_file_columns(files, is_personal=True)
        except Exception as e:
            print(f"Error getting personal files for display: {e}")
            return []

    def refresh_common_files_display(self) -> List[List[Any]]:
        """Refresh common knowledge files display"""
        try:
            return self.get_common_files_for_display()
        except Exception as e:
            print(f"Error refreshing common files display: {e}")
            return []

    def refresh_personal_files_display(self) -> List[List[Any]]:
        """Refresh personal files display"""
        try:
            return self.get_personal_files_for_display()
        except Exception as e:
            print(f"Error refreshing personal files display: {e}")
            return []

    def search_common_files_display(self, search_term: str) -> List[List[Any]]:
        """Search common knowledge files"""
        try:
            return self.get_common_files_for_display(search_term)
        except Exception as e:
            print(f"Error searching common files: {e}")
            return []

    def search_personal_files_display(self, search_term: str) -> List[List[Any]]:
        """Search personal files"""
        try:
            return self.get_personal_files_for_display(search_term)
        except Exception as e:
            print(f"Error searching personal files: {e}")
            return []

    def load_files_tab_data(self) -> Tuple[List[List[Any]], List[List[Any]]]:
        """Load both common and personal files for Files tab"""
        try:
            common_files = self.get_common_files_for_display()
            personal_files = self.get_personal_files_for_display()
            return common_files, personal_files
        except Exception as e:
            print(f"Error loading files tab data: {e}")
            return [], []
    
    # ========== COMMON KNOWLEDGE OPERATIONS ==========
    
    def handle_common_knowledge_upload(self, files) -> Tuple[List[List[Any]], str, List[str], str]:
        """Handle common knowledge file upload"""
        if not self.is_admin():
            notification = '<div class="notification">❌ Access denied - Admin only</div>'
            return [], "Access denied", [], notification
        
        try:
            from file_services import enhanced_file_service
            
            files_list, status, choices = enhanced_file_service.upload_common_knowledge_files(
                files, self.current_user["email"]
            )
            
            success_count = status.count("✅")
            notification = f'<div class="notification">📤 Upload Complete: {success_count} files processed</div>'
            
            return files_list, status, choices, notification
            
        except Exception as e:
            notification = '<div class="notification">❌ Upload failed</div>'
            return [], f"Upload error: {str(e)}", [], notification
    
    def handle_common_knowledge_delete(self, selected_files: List[str]) -> Tuple[List[List[Any]], str, List[str], str]:
        """Handle common knowledge file deletion"""
        if not self.is_admin():
            notification = '<div class="notification">❌ Access denied - Admin only</div>'
            return [], "Access denied", [], notification
        
        try:
            from file_services import enhanced_file_service
            
            files_list, status, choices = enhanced_file_service.delete_common_knowledge_files(selected_files)
            
            success_count = status.count("✅")
            notification = f'<div class="notification">🗑️ Deletion Complete: {success_count} files removed</div>'
            
            return files_list, status, choices, notification
            
        except Exception as e:
            notification = '<div class="notification">❌ Deletion failed</div>'
            return [], f"Delete error: {str(e)}", [], notification
    
    def handle_common_knowledge_refresh(self, search_term: str = "") -> Tuple[List[List[Any]], List[str], str]:
        """Handle common knowledge file refresh"""
        if not self.is_admin_or_spoc():
            notification = '<div class="notification">❌ Access denied</div>'
            return [], [], notification
        
        try:
            from file_services import enhanced_file_service
            
            files = enhanced_file_service.get_common_knowledge_file_list(search_term)
            choices = [row[0] for row in files] if files else []
            notification = '<div class="notification">🔄 Files refreshed</div>'
            
            return files, choices, notification
            
        except Exception as e:
            notification = '<div class="notification">❌ Refresh failed</div>'
            return [], [], notification
    
    def handle_common_knowledge_reindex(self) -> Tuple[List[List[Any]], List[str], str, str]:
        """Handle common knowledge re-indexing"""
        if not self.is_admin():
            notification = '<div class="notification">❌ Access denied - Admin only</div>'
            return [], [], "Access denied", notification
        
        try:
            from file_services import enhanced_file_service
            
            result = enhanced_file_service.reindex_common_knowledge_pending_files()
            files = enhanced_file_service.get_common_knowledge_file_list()
            choices = [row[0] for row in files] if files else []
            notification = '<div class="notification">🔍 Re-indexing Complete</div>'
            
            return files, choices, result, notification
            
        except Exception as e:
            notification = '<div class="notification">❌ Re-indexing failed</div>'
            return [], [], f"Re-indexing error: {str(e)}", notification
    
    def handle_common_knowledge_cleanup(self) -> Tuple[str, str]:
        """Handle common knowledge vector cleanup"""
        if not self.is_admin():
            notification = '<div class="notification">❌ Access denied - Admin only</div>'
            return "", notification
        
        try:
            from rag_service import rag_service
            
            result = rag_service.cleanup_common_knowledge_vectors()
            
            if result.get("status") == "success":
                cleanup_count = result.get("vector_entries_cleaned", 0)
                db_count = result.get("db_records_cleaned", 0)
                remaining = result.get("remaining_files", 0)
                orphaned = result.get("orphaned_files", [])
                
                status_msg = f"🧹 Vector Database Cleanup Complete:\n"
                status_msg += f"• Vector entries cleaned: {cleanup_count}\n"
                status_msg += f"• Database records cleaned: {db_count}\n"
                status_msg += f"• Files remaining: {remaining}\n"
                
                if orphaned:
                    status_msg += f"• Orphaned files removed: {len(orphaned)}\n"
                    status_msg += f"• Files: {', '.join(orphaned[:3])}" + ("..." if len(orphaned) > 3 else "")
                
                notification = '<div class="notification">🧹 Vector database cleaned successfully</div>'
            else:
                status_msg = f"❌ Cleanup failed: {result.get('message', 'Unknown error')}"
                notification = '<div class="notification">❌ Cleanup failed</div>'
            
            return status_msg, notification
            
        except Exception as e:
            status_msg = f"❌ Cleanup error: {str(e)}"
            notification = '<div class="notification">❌ Cleanup failed</div>'
            return status_msg, notification
    
    def handle_common_knowledge_vector_stats(self) -> Tuple[str, str]:
        """Handle common knowledge vector stats"""
        if not self.is_admin_or_spoc():
            notification = '<div class="notification">❌ Access denied</div>'
            return "", notification
        
        try:
            from rag_service import rag_service
            
            result = rag_service.get_common_knowledge_stats()
            
            vector_count = result.get("vector_entries", 0)
            fs_count = result.get("filesystem_files", 0)
            db_count = result.get("database_files", 0)
            sync_status = result.get("sync_status", "unknown")
            status_message = result.get("status_message", "")
            
            status_msg = f"📊 Vector Database Statistics:\n"
            status_msg += f"• Vector entries: {vector_count:,}\n"
            status_msg += f"• Filesystem files: {fs_count}\n"
            
            if db_count > 0:
                status_msg += f"• Database files: {db_count}\n"
            
            status_msg += f"• Sync status: {sync_status.upper()}\n"
            status_msg += f"• Status: {status_message}\n"
            
            if sync_status == "needs_cleanup":
                status_msg += f"• ⚠️ Cleanup recommended\n"
            elif sync_status == "synced":
                status_msg += f"• ✅ Database is synchronized\n"
            elif sync_status == "needs_indexing":
                status_msg += f"• 🔍 Files need indexing\n"
            
            if result.get("error"):
                status_msg += f"• Error: {result['error']}"
            
            notification = '<div class="notification">📊 Stats updated successfully</div>'
            return status_msg, notification
            
        except Exception as e:
            status_msg = f"❌ Stats error: {str(e)}"
            notification = '<div class="notification">❌ Stats failed</div>'
            return status_msg, notification
    
    def search_common_knowledge_files(self, search_term: str) -> Tuple[List[List[Any]], List[str]]:
        """Search common knowledge files"""
        try:
            from file_services import enhanced_file_service
            
            files = enhanced_file_service.get_common_knowledge_file_list(search_term)
            choices = [row[0] for row in files] if files else []
            
            return files, choices
            
        except Exception as e:
            print(f"Error searching common knowledge files: {e}")
            return [], []
    
    # ========== USER FILE OPERATIONS ==========
    
    def handle_user_file_upload(self, user_email: str, files) -> Tuple[List[List[Any]], str, List[str], str]:
        """Handle user file upload"""
        if not self.is_admin() or not user_email:
            notification = '<div class="notification">❌ Admin access required and user must be selected</div>'
            return [], "Access denied or no user selected", [], notification
        
        try:
            from file_services import enhanced_file_service
            
            files_list, status, choices = enhanced_file_service.upload_user_files(user_email, files)
            
            success_count = status.count("✅")
            notification = f'<div class="notification">📤 Upload Complete: {success_count} files for user</div>'
            
            return files_list, status, choices, notification
            
        except Exception as e:
            notification = '<div class="notification">❌ Upload failed</div>'
            return [], f"Upload error: {str(e)}", [], notification
    
    def handle_user_file_delete(self, user_email: str, selected_files: List[str]) -> Tuple[List[List[Any]], str, List[str], str]:
        """Handle user file deletion"""
        if not self.is_admin() or not user_email:
            notification = '<div class="notification">❌ Admin access required and user must be selected</div>'
            return [], "Access denied or no user selected", [], notification
        
        try:
            from file_services import enhanced_file_service
            
            files_list, status, choices = enhanced_file_service.delete_user_files(user_email, selected_files)
            
            success_count = status.count("✅")
            notification = f'<div class="notification">🗑️ Deletion Complete: {success_count} files removed</div>'
            
            return files_list, status, choices, notification
            
        except Exception as e:
            notification = '<div class="notification">❌ Deletion failed</div>'
            return [], f"Delete error: {str(e)}", [], notification
    
    def handle_user_file_refresh(self, user_email: str, search_term: str = "") -> Tuple[List[List[Any]], List[str], str]:
        """Handle user file refresh"""
        if not self.is_admin() or not user_email:
            notification = '<div class="notification">❌ Admin access required and user must be selected</div>'
            return [], [], notification
        
        try:
            from file_services import enhanced_file_service
            
            files = enhanced_file_service.get_user_file_list(user_email, search_term)
            choices = [row[0] for row in files] if files else []
            notification = '<div class="notification">🔄 User files refreshed</div>'
            
            return files, choices, notification
            
        except Exception as e:
            notification = '<div class="notification">❌ Refresh failed</div>'
            return [], [], notification
    
    def handle_user_file_reindex(self, user_email: str) -> Tuple[str, str]:
        """Handle user file re-indexing"""
        if not self.is_admin() or not user_email:
            notification = '<div class="notification">❌ Admin access required and user must be selected</div>'
            return "Access denied or no user selected", notification
        
        try:
            from file_services import enhanced_file_service
            
            result = enhanced_file_service.reindex_user_pending_files(user_email)
            notification = '<div class="notification">🔍 User re-indexing completed</div>'
            
            return result, notification
            
        except Exception as e:
            notification = '<div class="notification">❌ Re-indexing failed</div>'
            return f"Re-indexing error: {str(e)}", notification
    
    def handle_user_vector_cleanup(self, user_email: str) -> Tuple[str, str]:
        """Handle user vector cleanup"""
        if not self.is_admin() or not user_email:
            notification = '<div class="notification">❌ Admin access required and user must be selected</div>'
            return "Access denied or no user selected", notification
        
        try:
            from rag_service import rag_service
            
            result = rag_service.cleanup_user_orphaned_vectors(user_email)
            
            if result.get("status") == "success":
                cleanup_count = result.get("vector_entries_cleaned", 0)
                remaining = result.get("remaining_files", 0)
                orphaned = result.get("orphaned_files", [])
                
                status_msg = f"🧹 User Vector Cleanup Complete for {user_email}:\n"
                status_msg += f"• Vector entries cleaned: {cleanup_count}\n"
                status_msg += f"• Files remaining: {remaining}\n"
                
                if orphaned:
                    status_msg += f"• Orphaned files removed: {len(orphaned)}\n"
                    status_msg += f"• Files: {', '.join(orphaned[:3])}" + ("..." if len(orphaned) > 3 else "")
                
                notification = '<div class="notification">🧹 User vector database cleaned successfully</div>'
            else:
                status_msg = f"❌ Cleanup failed: {result.get('message', 'Unknown error')}"
                notification = '<div class="notification">❌ Cleanup failed</div>'
            
            return status_msg, notification
            
        except Exception as e:
            status_msg = f"❌ Cleanup error: {str(e)}"
            notification = '<div class="notification">❌ Cleanup failed</div>'
            return status_msg, notification
    
    def handle_user_vector_stats(self, user_email: str) -> Tuple[str, str]:
        """Handle user vector stats"""
        if not self.is_admin() or not user_email:
            notification = '<div class="notification">❌ Admin access required and user must be selected</div>'
            return "Access denied or no user selected", notification
        
        try:
            from rag_service import rag_service
            
            result = rag_service.get_user_vector_stats(user_email)
            
            vector_count = result.get("vector_entries", 0)
            fs_count = result.get("filesystem_files", 0)
            sync_status = result.get("sync_status", "unknown")
            status_message = result.get("status_message", "")
            
            status_msg = f"📊 User Vector Statistics for {user_email}:\n"
            status_msg += f"• Vector entries: {vector_count:,}\n"
            status_msg += f"• Filesystem files: {fs_count}\n"
            status_msg += f"• Sync status: {sync_status.upper()}\n"
            status_msg += f"• Status: {status_message}\n"
            
            if result.get("error"):
                status_msg += f"• Error: {result['error']}"
            
            notification = '<div class="notification">📊 User stats updated successfully</div>'
            return status_msg, notification
            
        except Exception as e:
            status_msg = f"❌ Stats error: {str(e)}"
            notification = '<div class="notification">❌ Stats failed</div>'
            return status_msg, notification
    
    def search_user_files(self, user_email: str, search_term: str) -> Tuple[List[List[Any]], List[str]]:
        """Search user files"""
        if not user_email:
            return [], []
        
        try:
            from file_services import enhanced_file_service
            
            files = enhanced_file_service.get_user_file_list(user_email, search_term)
            choices = [row[0] for row in files] if files else []
            
            return files, choices
            
        except Exception as e:
            print(f"Error searching user files: {e}")
            return [], []

# Global UI service instance
ui_service = EnhancedUIService()