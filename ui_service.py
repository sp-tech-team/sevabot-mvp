import os
import threading
import webbrowser
from typing import List, Dict, Optional, Tuple, Any
import gradio as gr

from constants import MAX_SESSIONS_PER_USER, ERROR_MESSAGES
from chat_service import chat_service
from file_service import file_service
from rag_service import rag_service

class UIService:
    """Service layer for UI interactions"""
    
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
    
    def is_logged_in(self) -> bool:
        """Check if user is logged in"""
        return bool(self.current_user.get("email"))
    
    def get_display_name(self) -> str:
        """Get user's display name from current user data"""
        name = self.current_user.get("name", "")
        email = self.current_user.get("email", "")
        
        # If we have a name, use the first part
        if name and name != "User":
            first_name = name.split()[0]
            return first_name
        
        # Fallback to email username if no name
        if email:
            email_name = email.split("@")[0]
            if email_name:
                first_name = email_name.replace(".", " ").title().split()[0]
                return first_name
        
        return "Friend"
    
    def get_last_assistant_message_id(self) -> Optional[str]:
        """Get the last assistant message ID for feedback"""
        return self.last_assistant_message_id
    
    def submit_feedback(self, message_id: str, feedback: str) -> bool:
        """Submit feedback for a message"""
        try:
            success = chat_service.update_message_feedback(message_id, feedback)
            return success
        except Exception as e:
            print(f"Error submitting feedback: {e}")
            return False
    
    # ========== CHAT METHODS ==========
    
    def load_initial_data(self) -> Tuple[str, gr.update]:
        """Load initial data for UI"""
        greeting = f"## 🤖 Sevabot - Welcome {self.get_display_name()}!"
        
        # Load conversations
        conversations = chat_service.get_user_conversations(self.current_user["email"])
        session_choices = [(conv["title"], conv["id"]) for conv in conversations]
        
        sessions_update = gr.update(choices=session_choices, value=None)
        
        return greeting, sessions_update
    
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
            user_msg_id = chat_service.store_message(conversation_id, "user", message)
            
            # Get conversation history for context
            conv_history = chat_service.get_conversation_history(conversation_id)
            
            # Generate response
            response = chat_service.create_rag_response(
                self.current_user["email"], 
                message, 
                conv_history
            )
            
            # Store assistant message and save message ID for feedback
            assistant_msg_id = chat_service.store_message(conversation_id, "assistant", response)
            self.last_assistant_message_id = assistant_msg_id
            
            # Update conversation timestamp
            chat_service.update_conversation_timestamp(conversation_id)
            
            # Update history
            new_history = (history or []) + [[message, response]]
            
            # Update sessions list
            conversations = chat_service.get_user_conversations(self.current_user["email"])
            session_choices = [(conv["title"], conv["id"]) for conv in conversations]
            sessions_update = gr.update(choices=session_choices, value=conversation_id)
            
            return new_history, "", conversation_id, sessions_update, ""
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            return (history or []) + [[message, error_msg]], "", conversation_id, gr.update(), error_msg
    
    def load_conversation(self, conversation_id: Optional[str]) -> Tuple[List[List[str]], Optional[str], str]:
        """Load conversation history with proper feedback restoration"""
        if not conversation_id:
            return [], None, ""
        
        try:
            self.current_conversation_id = conversation_id
            
            # Get messages from database with feedback
            from supabase import create_client
            from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            
            result = supabase.table("messages")\
                .select("*")\
                .eq("conversation_id", conversation_id)\
                .order("created_at")\
                .execute()
            
            if not result.data:
                return [], conversation_id, "✅ Empty conversation loaded"
            
            # Build conversation history with feedback
            gradio_history = []
            user_msg = None
            
            for msg in result.data:
                if msg["role"] == "user":
                    user_msg = msg["content"]
                elif msg["role"] == "assistant" and user_msg:
                    assistant_content = msg["content"]
                    
                    # Process feedback if it exists
                    if msg.get("feedback"):
                        feedback_data = str(msg["feedback"]).strip()
                        
                        if feedback_data and feedback_data != "None":
                            # Parse feedback - handle both new format (type:remarks) and old format (just type)
                            if ":" in feedback_data:
                                try:
                                    feedback_parts = feedback_data.split(":", 1)
                                    feedback_type = feedback_parts[0].strip().lower()
                                    remarks = feedback_parts[1].strip() if len(feedback_parts) > 1 else ""
                                except:
                                    feedback_type = feedback_data.lower()
                                    remarks = ""
                            else:
                                feedback_type = feedback_data.lower()
                                remarks = ""
                            
                            # Get emoji for feedback type
                            feedback_emoji = {
                                "good": "👍", 
                                "neutral": "😐", 
                                "bad": "👎"
                            }
                            
                            emoji = feedback_emoji.get(feedback_type, "")
                            feedback_display = f"{emoji} {feedback_type.title()}"
                            
                            # Add remarks if they exist
                            if remarks:
                                feedback_display += f" - {remarks}"
                            
                            # Append feedback to assistant content
                            assistant_content += f"\n\n*[Feedback: {feedback_display}]*"
                    
                    gradio_history.append([user_msg, assistant_content])
                    user_msg = None
            
            return gradio_history, conversation_id, f"✅ Loaded conversation with {len(gradio_history)} messages"
            
        except Exception as e:
            print(f"Error loading conversation: {e}")
            # Fallback to original method without feedback
            history = chat_service.get_conversation_history(conversation_id)
            gradio_history = [[user_msg, assistant_msg] for user_msg, assistant_msg in history]
            return gradio_history, conversation_id, f"✅ Loaded conversation with {len(gradio_history)} messages (feedback unavailable)"
    
    def create_new_chat(self) -> Tuple[List[List[str]], Optional[str], gr.update, str]:
        """Create new chat with personalized greeting"""
        existing_conversations = chat_service.get_user_conversations(self.current_user["email"])
        if len(existing_conversations) >= MAX_SESSIONS_PER_USER:
            return [], None, gr.update(), ERROR_MESSAGES["session_limit"]
        
        self.current_conversation_id = None
        
        # Create personalized greeting with user's name
        user_name = self.get_display_name()
        base_greeting = self.get_random_namaskaram_greeting()
        personalized_greeting = f"🙏 Namaskaram {user_name}! {base_greeting}"
        
        # Set initial history with personalized greeting
        initial_history = [["", personalized_greeting]]
        
        # Refresh sessions list
        conversations = chat_service.get_user_conversations(self.current_user["email"])
        session_choices = [(conv["title"], conv["id"]) for conv in conversations]
        sessions_update = gr.update(choices=session_choices, value=None)
        
        return initial_history, None, sessions_update, "✅ New chat ready"
    
    def delete_conversation(self, conversation_id: Optional[str]) -> Tuple[List[List[str]], Optional[str], gr.update, str]:
        """Delete conversation"""
        if not conversation_id:
            return [], None, gr.update(), "⚠️ No conversation selected"
        
        try:
            success = chat_service.delete_conversation(conversation_id, self.current_user["email"])
            
            if success:
                if self.current_conversation_id == conversation_id:
                    self.current_conversation_id = None
                
                conversations = chat_service.get_user_conversations(self.current_user["email"])
                session_choices = [(conv["title"], conv["id"]) for conv in conversations]
                sessions_update = gr.update(choices=session_choices, value=None)
                
                return [], None, sessions_update, "✅ Conversation deleted"
            else:
                return [], conversation_id, gr.update(), "⚠️ Failed to delete conversation"
                
        except Exception as e:
            return [], conversation_id, gr.update(), f"⚠️ Error: {str(e)}"
    
    # ========== FILE METHODS ==========
    
    def upload_files_with_progress(self, files) -> Tuple[gr.update, str, gr.update]:
        """Upload files with enhanced error handling and progress updates"""
        if not files:
            return gr.update(), "⚠️ No files selected", gr.update()

        try:
            # Normalize file paths
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
                return gr.update(), "⚠️ No valid file paths found", gr.update()

            uploaded_count = 0
            total_chunks = 0
            errors = []
            status_updates = []

            for i, file_path in enumerate(file_paths):
                if not file_path or not os.path.exists(file_path):
                    errors.append(f"File not found: {file_path}")
                    continue
                    
                file_name = os.path.basename(file_path)
                status_updates.append(f"📤 Processing file {i+1}/{len(file_paths)}: {file_name}")
                
                try:
                    # Upload file
                    success, message = file_service.upload_file(self.current_user["email"], file_path)
                    
                    if success:
                        uploaded_count += 1
                        status_updates.append(f"✅ Uploaded: {file_name}")
                        
                        # Index document with retries
                        index_success = False
                        retry_count = 0
                        max_retries = 3
                        
                        while retry_count < max_retries and not index_success:
                            try:
                                index_success, index_msg, chunks_count = rag_service.index_user_document(
                                    self.current_user["email"], file_name
                                )
                                
                                if index_success:
                                    total_chunks += chunks_count
                                    status_updates.append(f"🔍 Indexed: {file_name} ({chunks_count} chunks)")
                                else:
                                    retry_count += 1
                                    if retry_count < max_retries:
                                        status_updates.append(f"⏳ Retrying indexing for {file_name} (attempt {retry_count + 1})")
                                    else:
                                        errors.append(f"{file_name}: indexing failed after {max_retries} attempts - {index_msg}")
                                        status_updates.append(f"❌ Indexing failed: {file_name}")
                                        
                            except Exception as index_error:
                                retry_count += 1
                                if retry_count < max_retries:
                                    status_updates.append(f"⏳ Retrying indexing for {file_name} due to error (attempt {retry_count + 1})")
                                else:
                                    errors.append(f"{file_name}: indexing error after {max_retries} attempts - {str(index_error)}")
                                    status_updates.append(f"❌ Indexing error: {file_name}")
                    else:
                        errors.append(f"{file_name}: {message}")
                        status_updates.append(f"❌ Upload failed: {file_name} - {message}")
                        
                except Exception as e:
                    errors.append(f"{file_name}: {str(e)}")
                    status_updates.append(f"❌ Error: {file_name} - {str(e)}")

            # Create final status message
            final_status = "\n".join(status_updates)
            if uploaded_count > 0:
                final_status += f"\n\n🎉 COMPLETED: {uploaded_count} file(s) uploaded with {total_chunks} total chunks"
            if errors:
                final_status += f"\n\n⚠️ ERRORS ({len(errors)} files failed):\n" + "\n".join([f"• {error}" for error in errors])

            # Update file list
            files_list = self.get_file_list()
            files_update = gr.update(value=files_list)
            choices = [row[0] for row in files_list] if files_list else []
            choices_update = gr.update(choices=choices, value=[])
            
            return files_update, final_status, choices_update
            
        except Exception as e:
            return gr.update(), f"⚠️ Upload system error: {str(e)}", gr.update()

    def delete_files_with_progress(self, selected_files: List[str]) -> Tuple[gr.update, str, gr.update]:
        """Delete files with progress updates"""
        if not selected_files:
            return gr.update(), "⚠️ No files selected", gr.update()
        
        try:
            deleted_count = 0
            errors = []
            status_updates = []

            for i, file_name in enumerate(selected_files):
                status_updates.append(f"🗑️ Deleting file {i+1}/{len(selected_files)}: {file_name}")
                
                try:
                    # Remove from vector store first
                    rag_service.remove_user_document(self.current_user["email"], file_name)
                    status_updates.append(f"🔍 Removed from index: {file_name}")
                    
                    # Delete file
                    success, message = file_service.delete_file(self.current_user["email"], file_name)
                    
                    if success:
                        deleted_count += 1
                        status_updates.append(f"✅ Deleted: {file_name}")
                    else:
                        errors.append(f"{file_name}: {message}")
                        status_updates.append(f"❌ Failed: {file_name} - {message}")
                        
                except Exception as e:
                    errors.append(f"{file_name}: {str(e)}")
                    status_updates.append(f"❌ Error: {file_name} - {str(e)}")

            final_status = "\n".join(status_updates)
            if deleted_count > 0:
                final_status += f"\n\n🎉 COMPLETED: {deleted_count} file(s) deleted successfully"
            if errors:
                final_status += f"\n\n⚠️ ERRORS ({len(errors)} files failed):\n" + "\n".join([f"• {error}" for error in errors])

            files_list = self.get_file_list()
            files_update = gr.update(value=files_list)
            choices = [row[0] for row in files_list] if files_list else []
            choices_update = gr.update(choices=choices, value=[])
            
            return files_update, final_status, choices_update
            
        except Exception as e:
            return gr.update(), f"⚠️ Delete error: {str(e)}", gr.update()
    
    def get_file_list(self) -> List[List[Any]]:
        """Get formatted file list for display with enhanced status information"""
        try:
            files = file_service.list_user_files(self.current_user["email"])
            
            file_list = []
            for file_info in files:
                chunks_count = file_info.get("chunks_count", 0)
                if chunks_count > 0:
                    status = "✅ Indexed"
                else:
                    # More informative pending status
                    if file_info["file_name"].lower().endswith('.pdf'):
                        status = "⚠️ Pending (May be image-based PDF - see guidelines above)"
                    else:
                        status = "⏳ Pending (Processing failed)"
                
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
    
    def get_random_namaskaram_greeting(self) -> str:
        """Get a random namaskaram greeting for new chats"""
        import random
        base_greetings = [
            "Ready to dive into your digital dharma library?",
            "Let's explore what wisdom your documents hold today!",
            "Your seva companion is here - what shall we discover?",
            "Time to unlock some knowledge karma from your files!",
            "I'm here for your document darshan - ask away!",
            "Let's turn your PDFs into prasadam of wisdom!",
            "Ready for some digital satsang with your documents?",
            "Your friendly document guru is at your seva!",
            "What treasures shall we find in your knowledge vault today?",
            "Time for some enlightening document exploration together!"
        ]
        return random.choice(base_greetings)
    
    def reindex_pending_files(self) -> str:
        """Re-index files that show as pending with enhanced error handling"""
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
                    # Multiple retry attempts for problematic files
                    success = False
                    last_error = None
                    
                    for attempt in range(3):
                        try:
                            success, msg, chunks = rag_service.index_user_document(
                                self.current_user["email"], file_name
                            )
                            if success:
                                reindexed += 1
                                break
                            else:
                                last_error = msg
                        except Exception as e:
                            last_error = str(e)
                            continue
                    
                    if not success:
                        errors.append(f"{file_name}: {last_error}")
                        
                except Exception as e:
                    errors.append(f"{file_name}: {str(e)}")
            
            result = f"✅ Re-indexed {reindexed} files"
            if errors:
                result += f"\n\n⚠️ ERRORS ({len(errors)} files failed):\n" + "\n".join([f"• {error}" for error in errors])
            
            return result
            
        except Exception as e:
            return f"⚠️ Error re-indexing: {str(e)}"

# Global UI service instance
ui_service = UIService()