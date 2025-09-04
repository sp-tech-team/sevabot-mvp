import os
import threading
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
import gradio as gr

from constants import MAX_SESSIONS_PER_USER, ERROR_MESSAGES
from chat_service import chat_service
from file_service import file_service
from rag_service import rag_service
from config import RAG_DOCUMENTS_PATH

class UIService:
    """Enhanced service layer for UI interactions with vector database cleanup"""
    
    def __init__(self):
        self.current_user = {"email": "", "name": "User", "user_id": ""}
        self.current_conversation_id = None
        self.last_assistant_message_id = None
        self._lock = threading.Lock()
    
    def set_user(self, user_data: Dict):
        """Set current user"""
        with self._lock:
            self.current_user = {
                "email": user_data.get("email", ""),
                "name": user_data.get("name", "User"),
                "user_id": user_data.get("user_id", "")
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
    
    def get_last_assistant_message_id(self) -> Optional[str]:
        return self.last_assistant_message_id
    
    def submit_feedback(self, message_id: str, feedback: str) -> bool:
        try:
            return chat_service.update_message_feedback(message_id, feedback)
        except Exception as e:
            print(f"Error submitting feedback: {e}")
            return False
    
    # ========== CHAT METHODS ==========
    
    def load_initial_data(self) -> Tuple[str, gr.update]:
        """Load initial data for UI"""
        conversations = chat_service.get_user_conversations(self.current_user["email"])
        session_choices = [(conv["title"], conv["id"]) for conv in conversations]
        return "", gr.update(choices=session_choices, value=None)
    
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
            
            # Generate response
            response = chat_service.create_rag_response(self.current_user["email"], message, conv_history)
            
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
            from supabase import create_client
            from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            
            result = supabase.table("messages")\
                .select("*")\
                .eq("conversation_id", conversation_id)\
                .order("created_at")\
                .execute()
            
            if not result.data:
                return [], conversation_id, "Empty conversation loaded"
            
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
                            
                            feedback_emoji = {"good": "👍", "neutral": "😐", "bad": "👎"}
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
        greeting = f"Namaskaram {user_name}! Ready to explore your documents?"
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
    
    # ========== FILE METHODS ==========
    
    def upload_files_with_progress(self, files) -> Tuple[gr.update, str, gr.update]:
        """Upload files with progress tracking"""
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
                    success, message = file_service.upload_file(self.current_user["email"], file_path)
                    
                    if success:
                        uploaded_count += 1
                        status_updates.append(f"✅ Uploaded: {file_name}")
                        
                        # Index with retries
                        for attempt in range(3):
                            try:
                                index_success, index_msg, chunks_count = rag_service.index_user_document(
                                    self.current_user["email"], file_name
                                )
                                
                                if index_success:
                                    total_chunks += chunks_count
                                    status_updates.append(f"🔍 Indexed: {file_name} ({chunks_count} chunks)")
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
                final_status += f"\n\n🎉 COMPLETED: {uploaded_count} files uploaded with {total_chunks} chunks"
            if errors:
                final_status += f"\n\n⚠️ ERRORS:\n" + "\n".join([f"• {error}" for error in errors])

            files_list = self.get_file_list()
            files_update = gr.update(value=files_list)
            choices = [row[0] for row in files_list] if files_list else []
            choices_update = gr.update(choices=choices, value=[])
            
            return files_update, final_status, choices_update
            
        except Exception as e:
            return gr.update(), f"Upload error: {str(e)}", gr.update()

    def delete_files_with_progress(self, selected_files: List[str]) -> Tuple[gr.update, str, gr.update]:
        """Delete files with progress tracking"""
        if not selected_files:
            return gr.update(), "No files selected", gr.update()
        
        try:
            deleted_count = 0
            errors = []
            status_updates = []

            for i, file_name in enumerate(selected_files):
                status_updates.append(f"Deleting {i+1}/{len(selected_files)}: {file_name}")
                
                try:
                    rag_service.remove_user_document(self.current_user["email"], file_name)
                    success, message = file_service.delete_file(self.current_user["email"], file_name)
                    
                    if success:
                        deleted_count += 1
                        status_updates.append(f"✅ Deleted: {file_name}")
                    else:
                        errors.append(f"{file_name}: {message}")
                        
                except Exception as e:
                    errors.append(f"{file_name}: {str(e)}")

            final_status = "\n".join(status_updates)
            if deleted_count > 0:
                final_status += f"\n\n🎉 COMPLETED: {deleted_count} files deleted"
            if errors:
                final_status += f"\n\n⚠️ ERRORS:\n" + "\n".join([f"• {error}" for error in errors])

            files_list = self.get_file_list()
            files_update = gr.update(value=files_list)
            choices = [row[0] for row in files_list] if files_list else []
            choices_update = gr.update(choices=choices, value=[])
            
            return files_update, final_status, choices_update
            
        except Exception as e:
            return gr.update(), f"Delete error: {str(e)}", gr.update()
    
    def get_file_list(self) -> List[List[Any]]:
        """Get formatted file list for display"""
        try:
            files = file_service.list_user_files(self.current_user["email"])
            
            file_list = []
            for file_info in files:
                chunks_count = file_info.get("chunks_count", 0)
                status = "✅ Indexed" if chunks_count > 0 else "⏳ Pending"
                
                file_list.append([
                    file_info["file_name"],
                    f"{file_info['file_size'] / 1024:.1f} KB",
                    chunks_count,
                    status,
                    file_info["uploaded_at"][:10]
                ])
            
            return file_list
            
        except Exception as e:
            print(f"Error getting file list: {e}")
            return []
    
    def reindex_pending_files(self) -> str:
        """Re-index files that failed initial indexing"""
        try:
            files = file_service.list_user_files(self.current_user["email"])
            pending_files = [f for f in files if f.get("chunks_count", 0) == 0]
            
            if not pending_files:
                return "✅ No pending files found"
            
            reindexed = 0
            errors = []
            
            for file_info in pending_files:
                file_name = file_info["file_name"]
                try:
                    for attempt in range(3):
                        success, msg, chunks = rag_service.index_user_document(
                            self.current_user["email"], file_name
                        )
                        if success:
                            reindexed += 1
                            break
                        elif attempt == 2:
                            errors.append(f"{file_name}: {msg}")
                        
                except Exception as e:
                    errors.append(f"{file_name}: {str(e)}")
            
            result = f"✅ Re-indexed {reindexed} files"
            if errors:
                result += f"\n\n⚠️ ERRORS:\n" + "\n".join([f"• {error}" for error in errors])
            
            return result
            
        except Exception as e:
            return f"Error re-indexing: {str(e)}"

    def cleanup_vector_database(self) -> str:
        """Clean up vector database by removing entries for files that don't exist on disk"""
        try:
            user_email = self.current_user["email"]
            
            # Get user's document folder
            user_documents_path = Path(RAG_DOCUMENTS_PATH) / user_email.replace("@", "_").replace(".", "_")
            
            if not user_documents_path.exists():
                return "✅ No user documents folder found - nothing to clean"
            
            # Get files from filesystem
            actual_files = set()
            for file_path in user_documents_path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.pdf', '.docx']:
                    actual_files.add(file_path.name)
            
            # Get user's vector store
            vectorstore = rag_service.get_user_vectorstore(user_email)
            collection = vectorstore._collection
            
            # Get all documents in vector store
            try:
                all_docs = collection.get()
                if not all_docs or not all_docs.get('metadatas'):
                    return "✅ Vector store is empty - nothing to clean"
                
                # Find orphaned entries (in vector store but not on disk)
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
                    # Delete in batches to avoid memory issues
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
                    from supabase import create_client
                    from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
                    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
                    
                    # Get all database records for this user
                    db_files = supabase.table("user_documents")\
                        .select("*")\
                        .eq("user_id", user_email)\
                        .execute()
                    
                    if db_files.data:
                        for db_file in db_files.data:
                            if db_file["file_name"] not in actual_files:
                                try:
                                    supabase.table("user_documents")\
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
                    result = f"🧹 CLEANUP COMPLETED:\n"
                    result += f"• Removed {cleanup_count} orphaned vector entries\n"
                    result += f"• Cleaned {db_cleanup_count} database records\n"
                    if orphaned_files:
                        result += f"• Files cleaned: {', '.join(sorted(orphaned_files))}\n"
                    result += f"• Remaining files on disk: {len(actual_files)}"
                    return result
                else:
                    return f"✅ Knowledge base is clean - {len(actual_files)} files verified"
                
            except Exception as e:
                return f"Error accessing vector store: {str(e)}"
            
        except Exception as e:
            return f"Error during cleanup: {str(e)}"

# Global UI service instance
ui_service = UIService()