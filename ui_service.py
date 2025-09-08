# ui_service.py - Enhanced with 3-tier role system and common knowledge repository
import os
import threading
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
import gradio as gr

from constants import MAX_SESSIONS_PER_USER, ERROR_MESSAGES, USER_ROLES
from chat_service import chat_service
from file_service import file_service
from rag_service import rag_service
from config import COMMON_KNOWLEDGE_PATH, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, IS_PRODUCTION
from supabase import create_client

class UIService:
    """Enhanced service layer for UI interactions with 3-tier role-based access control"""
    
    def __init__(self):
        self.current_user = {"email": "", "name": "User", "user_id": "", "role": "user"}
        self.current_conversation_id = None
        self.last_assistant_message_id = None
        self._lock = threading.Lock()
    
# ui_service.py - Enhanced with 3-tier role system and common knowledge repository
import os
import threading
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
import gradio as gr

from constants import MAX_SESSIONS_PER_USER, ERROR_MESSAGES, USER_ROLES
from chat_service import chat_service
from file_service import file_service
from rag_service import rag_service
from config import COMMON_KNOWLEDGE_PATH, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, IS_PRODUCTION
from supabase import create_client

class UIService:
    """Enhanced service layer for UI interactions with 3-tier role-based access control"""
    
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
        """Check if current user is admin"""
        return self.current_user.get("role") == USER_ROLES['admin']
    
    def is_spoc(self) -> bool:
        """Check if current user is SPOC"""
        return self.current_user.get("role") == USER_ROLES['spoc']
    
    def is_admin_or_spoc(self) -> bool:
        """Check if current user is admin or SPOC"""
        return self.is_admin() or self.is_spoc()
    
    def get_user_role(self) -> str:
        """Get current user role"""
        return self.current_user.get("role", "user")
    
    def get_last_assistant_message_id(self) -> Optional[str]:
        return self.last_assistant_message_id
    
    def submit_feedback(self, message_id: str, feedback: str) -> bool:
        try:
            return chat_service.update_message_feedback(message_id, feedback)
        except Exception as e:
            print(f"Error submitting feedback: {e}")
            return False
    
    # ========== USER MANAGEMENT ==========
    
    def get_all_users_for_admin(self) -> List[Dict]:
        """Get all users for admin management"""
        if not self.is_admin():
            return []
        
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            result = supabase.table("users")\
                .select("email, name, role, last_login")\
                .order("last_login", desc=True)\
                .execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting users: {e}")
            return []
    
    def get_assigned_users_for_spoc(self) -> List[str]:
        """Get users assigned to current SPOC"""
        if not self.is_spoc():
            return []
        
        return chat_service.get_spoc_assignments(self.current_user["email"])
    
    def get_all_spoc_assignments_for_admin(self) -> Dict[str, List[str]]:
        """Get all SPOC assignments (admin only)"""
        if not self.is_admin():
            return {}
        
        return chat_service.get_all_spoc_assignments()
    
    def add_spoc_assignment(self, spoc_email: str, user_email: str) -> bool:
        """Add user assignment to SPOC (admin only)"""
        if not self.is_admin():
            return False
        
        return chat_service.add_spoc_assignment(spoc_email, user_email)
    
    def remove_spoc_assignment(self, spoc_email: str, user_email: str) -> bool:
        """Remove user assignment from SPOC (admin only)"""
        if not self.is_admin():
            return False
        
        return chat_service.remove_spoc_assignment(spoc_email, user_email)
    
    def promote_user_to_spoc(self, user_email: str) -> bool:
        """Promote a user to SPOC role (admin only)"""
        if not self.is_admin():
            return False
        
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            result = supabase.table("users")\
                .update({"role": "spoc"})\
                .eq("email", user_email)\
                .execute()
            
            return bool(result.data)
        except Exception as e:
            print(f"Error promoting user to SPOC: {e}")
            return False
    
    def demote_spoc_to_user(self, spoc_email: str) -> bool:
        """Demote a SPOC back to regular user (admin only)"""
        if not self.is_admin():
            return False
        
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            
            # Remove all SPOC assignments first
            supabase.table("spoc_assignments")\
                .delete()\
                .eq("spoc_email", spoc_email)\
                .execute()
            
            # Update role to user
            result = supabase.table("users")\
                .update({"role": "user"})\
                .eq("email", spoc_email)\
                .execute()
            
            return bool(result.data)
        except Exception as e:
            print(f"Error demoting SPOC to user: {e}")
            return False
    
    def get_user_conversations_for_admin(self, target_user_email: str) -> List[Dict]:
        """Get conversations for specific user (admin/SPOC only)"""
        if not self.is_admin_or_spoc():
            return []
        
        try:
            conversations = chat_service.get_user_conversations(target_user_email)
            return conversations
        except Exception as e:
            print(f"ERROR: Error getting conversations for {target_user_email}: {e}")
            return []
    
    def get_spoc_assignments_for_spoc(self, spoc_email: str) -> List[str]:
        """Get users assigned to a SPOC"""
        try:
            return chat_service.get_spoc_assignments(spoc_email)
        except Exception as e:
            print(f"Error getting SPOC assignments: {e}")
            return []
    
    # ========== CHAT METHODS ==========
    
    def load_initial_data(self) -> Tuple[str, gr.update]:
        """Load initial data for UI - regular users see their own conversations"""
        # All users (including admins) start by seeing their own conversations
        conversations = chat_service.get_user_conversations(self.current_user["email"])
        session_choices = [(conv["title"], conv["id"]) for conv in conversations]
        
        return "", gr.update(choices=session_choices, value=None)
    
    def send_message(self, message: str, history: List[List[str]], conversation_id: Optional[str]) -> Tuple[List[List[str]], str, Optional[str], gr.update, str]:
        """Send message and get response from common knowledge repository"""
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
            
            # Update history and sessions (always use current user's conversations)
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
        
        # Always use current user's conversations
        conversations = chat_service.get_user_conversations(self.current_user["email"])
        session_choices = [(conv["title"], conv["id"]) for conv in conversations]
        sessions_update = gr.update(choices=session_choices, value=None)
        
        return initial_history, None, sessions_update, "New chat ready"
    
    def delete_conversation(self, conversation_id: Optional[str]) -> Tuple[List[List[str]], Optional[str], gr.update, str]:
        """Delete conversation (only own conversations for non-admins)"""
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
                
                # Always use current user's conversations
                conversations = chat_service.get_user_conversations(self.current_user["email"])
                session_choices = [(conv["title"], conv["id"]) for conv in conversations]
                sessions_update = gr.update(choices=session_choices, value=None)
                
                return [], None, sessions_update, "Conversation deleted"
            else:
                return [], conversation_id, gr.update(), "Failed to delete conversation"
                
        except Exception as e:
            return [], conversation_id, gr.update(), f"Error: {str(e)}"
    
    # ========== COMMON KNOWLEDGE FILE METHODS ==========
    
    def upload_files_to_common_knowledge(self, files) -> Tuple[gr.update, str, gr.update]:
        """Upload files to common knowledge repository (admin only)"""
        if not self.is_admin():
            return gr.update(), ERROR_MESSAGES["admin_only"], gr.update()
        
        if not files:
            return gr.update(), "No files selected", gr.update()

        try:
            file_paths = []
            if isinstance(files, list):
                for file_item in files:
                    if hasattr(file_item, 'name') and file_item.name:
                        file_paths.append(file_item.name)
                    elif isinstance(file_item, str) and file_item:
                        file_paths.append(file_item)
            else:
                if hasattr(files, 'name') and files.name:
                    file_paths = [files.name]
                elif isinstance(files, str) and files:
                    file_paths = [files]

            if not file_paths:
                return gr.update(), "No valid file paths found", gr.update()

            uploaded_count = 0
            total_chunks = 0
            errors = []
            status_updates = []

            for i, file_path in enumerate(file_paths):
                if not file_path or not os.path.exists(file_path):
                    errors.append(f"File not found: {file_path}")
                    continue
                    
                file_name = os.path.basename(file_path)
                status_updates.append(f"Processing {i+1}/{len(file_paths)}: {file_name}")
                
                try:
                    success, message = file_service.upload_file_to_common_knowledge(
                        file_path, self.current_user["email"]
                    )
                    
                    if success:
                        uploaded_count += 1
                        status_updates.append(f"✅ Uploaded: {file_name}")
                        
                        # Index with retries
                        for attempt in range(3):
                            try:
                                index_success, index_msg, chunks_count = rag_service.index_common_knowledge_document(file_name)
                                
                                if index_success:
                                    total_chunks += chunks_count
                                    status_updates.append(f"📚 Indexed: {file_name} ({chunks_count} chunks)")
                                    break
                                elif attempt == 2:
                                    errors.append(f"{file_name}: indexing failed - {index_msg}")
                                    
                            except Exception as e:
                                if attempt == 2:
                                    errors.append(f"{file_name}: indexing error - {str(e)}")
                    else:
                        errors.append(f"{file_name}: {message}")
                        
                except Exception as e:
                    errors.append(f"{file_name}: {str(e)}")

            final_status = "\n".join(status_updates)
            if uploaded_count > 0:
                final_status += f"\n\n🎉 COMPLETED: {uploaded_count} files uploaded to common knowledge repository with {total_chunks} chunks"
            if errors:
                final_status += f"\n\n⚠️ ERRORS:\n" + "\n".join([f"• {error}" for error in errors])

            files_list = self.get_common_knowledge_file_list()
            files_update = gr.update(value=files_list)
            choices = [row[0] for row in files_list] if files_list else []
            choices_update = gr.update(choices=choices, value=[])
            
            return files_update, final_status, choices_update
            
        except Exception as e:
            return gr.update(), f"Upload error: {str(e)}", gr.update()

    def delete_common_knowledge_files_with_progress(self, selected_files: List[str]) -> Tuple[gr.update, str, gr.update]:
        """Delete files from common knowledge repository with progress tracking (admin only)"""
        if not self.is_admin():
            return gr.update(), ERROR_MESSAGES["admin_only"], gr.update()
            
        if not selected_files:
            return gr.update(), "No files selected", gr.update()
        
        try:
            deleted_count = 0
            errors = []
            status_updates = []

            for i, file_name in enumerate(selected_files):
                status_updates.append(f"Deleting {i+1}/{len(selected_files)}: {file_name}")
                
                try:
                    rag_service.remove_common_knowledge_document(file_name)
                    success, message = file_service.delete_common_knowledge_file(file_name)
                    
                    if success:
                        deleted_count += 1
                        status_updates.append(f"✅ Deleted: {file_name}")
                    else:
                        errors.append(f"{file_name}: {message}")
                        
                except Exception as e:
                    errors.append(f"{file_name}: {str(e)}")

            final_status = "\n".join(status_updates)
            if deleted_count > 0:
                final_status += f"\n\n🎉 COMPLETED: {deleted_count} files deleted from common knowledge repository"
            if errors:
                final_status += f"\n\n⚠️ ERRORS:\n" + "\n".join([f"• {error}" for error in errors])

            files_list = self.get_common_knowledge_file_list()
            files_update = gr.update(value=files_list)
            choices = [row[0] for row in files_list] if files_list else []
            choices_update = gr.update(choices=choices, value=[])
            
            return files_update, final_status, choices_update
            
        except Exception as e:
            return gr.update(), f"Delete error: {str(e)}", gr.update()
    
    def get_common_knowledge_file_list(self, search_term: str = "") -> List[List[Any]]:
        """Get formatted file list for common knowledge repository with search - FIXED: Environment-aware chunk counts"""
        try:
            files = file_service.list_common_knowledge_files()
            
            file_list = []
            for file_info in files:
                # FIXED: Get actual chunks count from RAG service (environment-aware)
                chunks_count = rag_service.get_file_chunks_count(file_info["file_name"])
                status = "✅ Indexed" if chunks_count > 0 else "⏳ Pending"
                
                # Format file size
                file_size = file_info["file_size"]
                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                
                # Get file extension for type
                file_ext = Path(file_info["file_name"]).suffix.upper().replace(".", "")
                file_type = f"{file_ext} Document" if file_ext else "Document"
                
                file_row = [
                    file_info["file_name"],
                    size_str,
                    file_type,
                    chunks_count,  # FIXED: Use actual chunks count
                    status,
                    file_info["uploaded_at"][:10],
                    file_info.get("uploaded_by", "Unknown")
                ]
                
                # Apply search filter
                if search_term:
                    search_lower = search_term.lower()
                    searchable_text = " ".join([
                        file_info["file_name"].lower(),
                        file_type.lower(),
                        status.lower()
                    ])
                    if search_lower not in searchable_text:
                        continue
                
                file_list.append(file_row)
            
            return file_list
            
        except Exception as e:
            print(f"Error getting common knowledge file list: {e}")
            return []
    
    def get_common_knowledge_file_list_for_users(self) -> List[List[Any]]:
        """Get user-friendly file list for regular users (non-technical)"""
        try:
            files = file_service.list_common_knowledge_files()
            
            file_list = []
            for file_info in files:
                # Format file size
                file_size = file_info["file_size"]
                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                
                # Get file extension for type
                file_ext = Path(file_info["file_name"]).suffix.upper().replace(".", "")
                file_type = f"{file_ext} Document" if file_ext else "Document"
                
                # Uploaded date
                upload_date = file_info["uploaded_at"][:10]
                
                file_list.append([
                    file_info["file_name"],
                    size_str,
                    file_type,
                    upload_date
                ])
            
            return file_list
            
        except Exception as e:
            print(f"Error getting user file list: {e}")
            return []
    
    def reindex_common_knowledge_pending_files(self) -> str:
        """Re-index only files that are not yet indexed in common knowledge repository"""
        if not self.is_admin():
            return ERROR_MESSAGES["admin_only"]
        
        try:
            reindexed, total_pending, errors = rag_service.reindex_common_knowledge_pending_files()
            
            if total_pending == 0:
                return "✅ All files already indexed in common knowledge repository"
            
            result = f"📚 Re-indexing Summary for Common Knowledge Repository:\n"
            result += f"• Files processed: {reindexed}/{total_pending}\n"
            result += f"• Files skipped (already indexed): {total_pending - reindexed - len(errors)}"
            
            if reindexed > 0:
                result += f"\n✅ Successfully indexed: {reindexed} files"
            
            if errors:
                result += f"\n\n⚠️ ERRORS ({len(errors)}):\n" + "\n".join([f"• {error}" for error in errors])
            
            return result
            
        except Exception as e:
            return f"Error re-indexing: {str(e)}"

    def cleanup_common_knowledge_vector_database(self) -> str:
        """Clean up common knowledge vector database"""
        if not self.is_admin():
            return ERROR_MESSAGES["admin_only"]
        
        try:
            # Get common knowledge folder
            common_knowledge_path = file_service.get_common_knowledge_path()
            
            if not common_knowledge_path.exists():
                return "✅ No common knowledge folder found - nothing to clean"
            
            # Get files from filesystem
            actual_files = set()
            for file_path in common_knowledge_path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.pdf', '.docx']:
                    actual_files.add(file_path.name)
            
            # Get common knowledge vector store
            vectorstore = rag_service.get_common_knowledge_vectorstore()
            collection = vectorstore._collection
            
            # Get all documents in vector store
            try:
                all_docs = collection.get()
                if not all_docs or not all_docs.get('metadatas'):
                    return "✅ Vector store is empty - nothing to clean"
                
                # Find orphaned entries
                orphaned_ids = []
                orphaned_files = set()
                
                for doc_id, metadata in zip(all_docs['ids'], all_docs['metadatas']):
                    file_name = metadata.get('file_name') or metadata.get('source', '')
                    if file_name and file_name not in actual_files:
                        orphaned_ids.append(doc_id)
                        orphaned_files.add(file_name)
                
                # Remove orphaned entries
                cleanup_count = 0
                if orphaned_ids:
                    batch_size = 100
                    for i in range(0, len(orphaned_ids), batch_size):
                        batch_ids = orphaned_ids[i:i+batch_size]
                        try:
                            collection.delete(ids=batch_ids)
                            cleanup_count += len(batch_ids)
                        except Exception as e:
                            print(f"Error deleting batch {i//batch_size + 1}: {e}")
                
                # Clean up database records for non-existent files
                db_cleanup_count = 0
                try:
                    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
                    
                    db_files = supabase.table("common_knowledge_documents")\
                        .select("*")\
                        .execute()
                    
                    if db_files.data:
                        for db_file in db_files.data:
                            if db_file["file_name"] not in actual_files:
                                try:
                                    supabase.table("common_knowledge_documents")\
                                        .delete()\
                                        .eq("id", db_file["id"])\
                                        .execute()
                                    db_cleanup_count += 1
                                except Exception as e:
                                    print(f"Error deleting DB record for {db_file['file_name']}: {e}")
                
                except Exception as e:
                    print(f"Database cleanup error: {e}")
                
                # Prepare result message
                if cleanup_count > 0 or db_cleanup_count > 0:
                    result = f"🧹 CLEANUP COMPLETED for Common Knowledge Repository:\n"
                    result += f"• Removed {cleanup_count} orphaned vector entries\n"
                    result += f"• Cleaned {db_cleanup_count} database records\n"
                    if orphaned_files:
                        result += f"• Files cleaned: {', '.join(sorted(orphaned_files))}\n"
                    result += f"• Remaining files on disk: {len(actual_files)}"
                    return result
                else:
                    return f"✅ Knowledge repository is clean - {len(actual_files)} files verified"
                
            except Exception as e:
                return f"Error accessing vector store: {str(e)}"
            
        except Exception as e:
            return f"Error during cleanup: {str(e)}"

# Global UI service instance
ui_service = UIService()