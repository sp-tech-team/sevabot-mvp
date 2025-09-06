# ui_service.py - Enhanced with local/cloud file detection and vector status
import os
import threading
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
import gradio as gr

from constants import MAX_SESSIONS_PER_USER, ERROR_MESSAGES
from chat_service import chat_service
from file_service import file_service
from rag_service import rag_service
from config import RAG_DOCUMENTS_PATH, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, IS_PRODUCTION
from supabase import create_client

class UIService:
    """Enhanced service layer for UI interactions with role-based access control"""
    
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
        return self.current_user.get("role") == "admin"
    
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
    
    # ========== ADMIN USER MANAGEMENT ==========
    
    def get_all_users_for_admin(self) -> List[Dict]:
        """Get all users for admin file management"""
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
    
    def search_users(self, search_term: str) -> List[Dict]:
        """Search users by email or name (admin only)"""
        if not self.is_admin() or not search_term:
            return []
        
        users = self.get_all_users_for_admin()
        filtered_users = [
            user for user in users 
            if search_term.lower() in user['email'].lower() or 
               search_term.lower() in user['name'].lower()
        ]
        
        return filtered_users
    
    def get_enhanced_user_files_for_admin(self, target_user_email: str) -> List[List]:
        """Get files with local/cloud flags and vector status (admin only) - ENHANCED"""
        if not self.is_admin():
            return []
        
        try:
            # Get user's document folder
            user_folder = target_user_email.replace("@", "_").replace(".", "_")
            user_documents_path = Path(RAG_DOCUMENTS_PATH) / user_folder
            
            # Get files from filesystem
            local_files = set()
            if user_documents_path.exists():
                for file_path in user_documents_path.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.pdf', '.docx']:
                        local_files.add(file_path.name)
            
            # Get files from database (cloud)
            cloud_files = {}
            try:
                supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
                result = supabase.table("user_documents")\
                    .select("*")\
                    .eq("user_id", target_user_email)\
                    .order("uploaded_at", desc=True)\
                    .execute()
                
                if result.data:
                    for file_info in result.data:
                        cloud_files[file_info["file_name"]] = file_info
            except Exception as e:
                print(f"Error getting cloud files: {e}")
            
            # Get vector status
            vector_files = set()
            try:
                vectorstore = rag_service.get_user_vectorstore(target_user_email)
                collection = vectorstore._collection
                all_docs = collection.get()
                
                if all_docs and all_docs.get('metadatas'):
                    for metadata in all_docs['metadatas']:
                        file_name = metadata.get('file_name') or metadata.get('source', '')
                        if file_name:
                            vector_files.add(file_name)
            except Exception as e:
                print(f"Error getting vector status: {e}")
            
            # Combine all files
            all_files = local_files.union(set(cloud_files.keys()))
            file_list = []
            
            for file_name in sorted(all_files):
                # Determine source
                in_local = file_name in local_files
                in_cloud = file_name in cloud_files
                in_vector = file_name in vector_files
                
                if in_local and in_cloud:
                    source_flag = "🔄 Synced"
                elif in_local:
                    source_flag = "💾 Local"
                elif in_cloud:
                    source_flag = "☁️ Cloud"
                else:
                    source_flag = "❓ Unknown"
                
                # Vector status
                vector_status = "🔍 Indexed" if in_vector else "⏳ Not Indexed"
                
                # Get file info
                if in_cloud:
                    file_info = cloud_files[file_name]
                    file_size = f"{file_info['file_size'] / 1024:.1f} KB"
                    chunks_count = file_info.get("chunks_count", 0)
                    status = "✅ Ready" if chunks_count > 0 else "⏳ Pending"
                    uploaded_date = file_info["uploaded_at"][:10]
                elif in_local:
                    try:
                        file_path = user_documents_path / file_name
                        stat = file_path.stat()
                        file_size = f"{stat.st_size / 1024:.1f} KB"
                        chunks_count = 0
                        status = "📁 Local Only"
                        uploaded_date = "Unknown"
                    except:
                        file_size = "Unknown"
                        chunks_count = 0
                        status = "❓ Error"
                        uploaded_date = "Unknown"
                else:
                    file_size = "Unknown"
                    chunks_count = 0
                    status = "❓ Missing"
                    uploaded_date = "Unknown"
                
                file_list.append([
                    file_name,
                    file_size,
                    chunks_count,
                    status,
                    source_flag,
                    vector_status,
                    uploaded_date,
                    target_user_email
                ])
            
            print(f"DEBUG: Enhanced file list for {target_user_email}: {len(file_list)} files")
            return file_list
            
        except Exception as e:
            print(f"ERROR: Error getting enhanced files for {target_user_email}: {e}")
            return []
    
    def get_vector_database_stats(self, target_user_email: str) -> str:
        """Get detailed vector database statistics"""
        if not self.is_admin():
            return "Access denied"
        
        try:
            # Get user's document folder
            user_folder = target_user_email.replace("@", "_").replace(".", "_")
            user_documents_path = Path(RAG_DOCUMENTS_PATH) / user_folder
            
            # Count local files
            local_files = set()
            if user_documents_path.exists():
                for file_path in user_documents_path.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.pdf', '.docx']:
                        local_files.add(file_path.name)
            
            # Count database files
            cloud_files = set()
            try:
                supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
                result = supabase.table("user_documents")\
                    .select("file_name")\
                    .eq("user_id", target_user_email)\
                    .execute()
                
                if result.data:
                    cloud_files = {file_info["file_name"] for file_info in result.data}
            except Exception as e:
                print(f"Error getting cloud files: {e}")
            
            # Get vector store stats
            vector_count = 0
            vector_files = set()
            vector_file_chunks = {}
            
            try:
                vectorstore = rag_service.get_user_vectorstore(target_user_email)
                collection = vectorstore._collection
                vector_count = collection.count()
                
                all_docs = collection.get()
                if all_docs and all_docs.get('metadatas'):
                    for metadata in all_docs['metadatas']:
                        file_name = metadata.get('file_name') or metadata.get('source', '')
                        if file_name:
                            vector_files.add(file_name)
                            vector_file_chunks[file_name] = vector_file_chunks.get(file_name, 0) + 1
            except Exception as e:
                print(f"Error getting vector stats: {e}")
            
            # Generate report
            stats = f"📊 **Vector Database Statistics for {target_user_email}**\n\n"
            stats += f"**File Locations:**\n"
            stats += f"• Local files: {len(local_files)}\n"
            stats += f"• Database files: {len(cloud_files)}\n"
            stats += f"• Vector indexed files: {len(vector_files)}\n"
            stats += f"• Total vector chunks: {vector_count}\n\n"
            
            # Sync status
            synced_files = local_files.intersection(cloud_files)
            local_only = local_files - cloud_files
            cloud_only = cloud_files - local_files
            
            stats += f"**Sync Status:**\n"
            stats += f"• Synced (local + cloud): {len(synced_files)}\n"
            stats += f"• Local only: {len(local_only)}\n"
            stats += f"• Cloud only: {len(cloud_only)}\n\n"
            
            # Vector sync status
            vector_synced = vector_files.intersection(local_files.union(cloud_files))
            vector_orphaned = vector_files - local_files.union(cloud_files)
            missing_from_vector = local_files.union(cloud_files) - vector_files
            
            stats += f"**Vector Sync Status:**\n"
            stats += f"• Properly indexed: {len(vector_synced)}\n"
            stats += f"• Orphaned vectors: {len(vector_orphaned)}\n"
            stats += f"• Missing from vector: {len(missing_from_vector)}\n\n"
            
            if vector_file_chunks:
                stats += f"**Chunks per file:**\n"
                for file_name, chunk_count in sorted(vector_file_chunks.items()):
                    stats += f"• {file_name}: {chunk_count} chunks\n"
            
            if vector_orphaned:
                stats += f"\n**⚠️ Orphaned vectors (files no longer exist):**\n"
                for file_name in sorted(vector_orphaned):
                    stats += f"• {file_name}\n"
            
            if missing_from_vector:
                stats += f"\n**⏳ Files not indexed:**\n"
                for file_name in sorted(missing_from_vector):
                    stats += f"• {file_name}\n"
            
            return stats
            
        except Exception as e:
            return f"Error generating stats: {str(e)}"
    
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
        """Load conversation history with feedback - FIXED for messages format"""
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
            
            # FIXED: Create proper message format for Gradio
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
                    
                    # FIXED: Use tuple format instead of dictionary for Gradio compatibility
                    gradio_history.append([user_msg, assistant_content])
                    user_msg = None
            
            return gradio_history, conversation_id, f"Loaded conversation with {len(gradio_history)} messages"
            
        except Exception as e:
            print(f"Error loading conversation: {e}")
            history = chat_service.get_conversation_history(conversation_id)
            # FIXED: Ensure tuple format
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
        """Upload files for current user"""
        return self._upload_files_for_user(files, self.current_user["email"])
    
    def upload_files_for_user(self, files, target_user_email: str) -> Tuple[gr.update, str, gr.update]:
        """Upload files for specific user (admin only)"""
        if not self.is_admin():
            return gr.update(), ERROR_MESSAGES["admin_only"], gr.update()
        
        if not target_user_email:
            return gr.update(), "Please select a user first", gr.update()
        
        return self._upload_files_for_user(files, target_user_email)
    
    def _upload_files_for_user(self, files, user_email: str) -> Tuple[gr.update, str, gr.update]:
        """Internal method to upload files for any user"""
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
            
            user_display = user_email if self.is_admin() else "your account"

            for i, file_path in enumerate(file_paths):
                if not file_path or not os.path.exists(file_path):
                    errors.append(f"File not found: {file_path}")
                    continue
                    
                file_name = os.path.basename(file_path)
                status_updates.append(f"Processing {i+1}/{len(file_paths)}: {file_name} for {user_display}")
                
                try:
                    success, message = file_service.upload_file(user_email, file_path)
                    
                    if success:
                        uploaded_count += 1
                        status_updates.append(f"✅ Uploaded: {file_name}")
                        
                        # Index with retries
                        for attempt in range(3):
                            try:
                                index_success, index_msg, chunks_count = rag_service.index_user_document(
                                    user_email, file_name
                                )
                                
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
                final_status += f"\n\n🎉 COMPLETED: {uploaded_count} files uploaded for {user_display} with {total_chunks} chunks"
            if errors:
                final_status += f"\n\n⚠️ ERRORS:\n" + "\n".join([f"• {error}" for error in errors])

            files_list = self.get_file_list() if not self.is_admin() else []
            files_update = gr.update(value=files_list)
            choices = [row[0] for row in files_list] if files_list else []
            choices_update = gr.update(choices=choices, value=[])
            
            return files_update, final_status, choices_update
            
        except Exception as e:
            return gr.update(), f"Upload error: {str(e)}", gr.update()

    def delete_files_with_progress(self, selected_files: List[str], target_user_email: str = None) -> Tuple[gr.update, str, gr.update]:
        """Delete files with progress tracking"""
        if not selected_files:
            return gr.update(), "No files selected", gr.update()
        
        # Determine target user
        user_email = target_user_email if self.is_admin() and target_user_email else self.current_user["email"]
        
        try:
            deleted_count = 0
            errors = []
            status_updates = []
            
            user_display = user_email if self.is_admin() else "your account"

            for i, file_name in enumerate(selected_files):
                status_updates.append(f"Deleting {i+1}/{len(selected_files)}: {file_name} from {user_display}")
                
                try:
                    rag_service.remove_user_document(user_email, file_name)
                    success, message = file_service.delete_file(user_email, file_name)
                    
                    if success:
                        deleted_count += 1
                        status_updates.append(f"✅ Deleted: {file_name}")
                    else:
                        errors.append(f"{file_name}: {message}")
                        
                except Exception as e:
                    errors.append(f"{file_name}: {str(e)}")

            final_status = "\n".join(status_updates)
            if deleted_count > 0:
                final_status += f"\n\n🎉 COMPLETED: {deleted_count} files deleted from {user_display}"
            if errors:
                final_status += f"\n\n⚠️ ERRORS:\n" + "\n".join([f"• {error}" for error in errors])

            files_list = self.get_file_list() if not self.is_admin() else []
            files_update = gr.update(value=files_list)
            choices = [row[0] for row in files_list] if files_list else []
            choices_update = gr.update(choices=choices, value=[])
            
            return files_update, final_status, choices_update
            
        except Exception as e:
            return gr.update(), f"Delete error: {str(e)}", gr.update()
    
    def get_file_list(self) -> List[List[Any]]:
        """Get formatted file list for display (for current user)"""
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
    
    def reindex_pending_files(self, target_user_email: str = None) -> str:
        """Re-index only files that are not yet indexed - IMPROVED"""
        user_email = target_user_email if self.is_admin() and target_user_email else self.current_user["email"]
        
        try:
            reindexed, total_pending, errors = rag_service.reindex_only_pending_files(user_email)
            
            user_display = user_email if self.is_admin() else "your account"
            
            if total_pending == 0:
                return f"✅ All files already indexed for {user_display}"
            
            result = f"📚 Re-indexing Summary for {user_display}:\n"
            result += f"• Files processed: {reindexed}/{total_pending}\n"
            result += f"• Files skipped (already indexed): {total_pending - reindexed - len(errors)}"
            
            if reindexed > 0:
                result += f"\n✅ Successfully indexed: {reindexed} files"
            
            if errors:
                result += f"\n\n⚠️ ERRORS ({len(errors)}):\n" + "\n".join([f"• {error}" for error in errors])
            
            return result
            
        except Exception as e:
            return f"Error re-indexing: {str(e)}"

    def cleanup_vector_database(self, target_user_email: str = None) -> str:
        """Clean up vector database by removing entries for files that don't exist on disk"""
        user_email = target_user_email if self.is_admin() and target_user_email else self.current_user["email"]
        
        try:
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
                user_display = user_email if self.is_admin() else "your account"
                
                if cleanup_count > 0 or db_cleanup_count > 0:
                    result = f"🧹 CLEANUP COMPLETED for {user_display}:\n"
                    result += f"• Removed {cleanup_count} orphaned vector entries\n"
                    result += f"• Cleaned {db_cleanup_count} database records\n"
                    if orphaned_files:
                        result += f"• Files cleaned: {', '.join(sorted(orphaned_files))}\n"
                    result += f"• Remaining files on disk: {len(actual_files)}"
                    return result
                else:
                    return f"✅ Knowledge base is clean for {user_display} - {len(actual_files)} files verified"
                
            except Exception as e:
                return f"Error accessing vector store: {str(e)}"
            
        except Exception as e:
            return f"Error during cleanup: {str(e)}"
        
    def get_user_conversations_for_admin(self, target_user_email: str) -> List[Dict]:
        """Get conversations for specific user (admin only)"""
        if not self.is_admin():
            return []
        
        try:
            conversations = chat_service.get_user_conversations(target_user_email)
            return conversations
        except Exception as e:
            print(f"ERROR: Error getting conversations for {target_user_email}: {e}")
            return []
        
    def get_user_files_for_admin_from_db(self, target_user_email: str) -> List[List]:
        """Get files for specific user from database (admin only) - always uses production DB"""
        if not self.is_admin():
            return []
        
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            
            # Always query database for admin file management
            result = supabase.table("user_documents")\
                .select("*")\
                .eq("user_id", target_user_email)\
                .order("uploaded_at", desc=True)\
                .execute()
            
            files = result.data if result.data else []
            print(f"DEBUG: Found {len(files)} files in database for user {target_user_email}")
            
            file_list = []
            for file_info in files:
                chunks_count = file_info.get("chunks_count", 0)
                status = "✅ Indexed" if chunks_count > 0 else "⏳ Pending"
                
                file_list.append([
                    file_info["file_name"],
                    f"{file_info['file_size'] / 1024:.1f} KB",
                    chunks_count,
                    status,
                    file_info["uploaded_at"][:10],
                    target_user_email
                ])
            
            print(f"DEBUG: Processed file list from database: {file_list}")
            return file_list
            
        except Exception as e:
            print(f"ERROR: Error getting files from database for {target_user_email}: {e}")
            return []

# Global UI service instance
ui_service = UIService()