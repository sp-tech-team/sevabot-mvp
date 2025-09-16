# file_services.py - Complete file management with S3 storage integration
import os
import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

from config import (
    COMMON_KNOWLEDGE_PATH, RAG_DOCUMENTS_PATH, 
    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, IS_PRODUCTION, USE_S3_STORAGE
)
from constants import SUPPORTED_EXTENSIONS, MAX_FILE_SIZE_MB, ERROR_MESSAGES
from supabase import create_client
from s3_storage import s3_storage

class EnhancedFileService:
    """Unified file management service with S3 storage support"""
    
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        
        # Create local directories for temp processing (always needed)
        self.common_knowledge_path = Path(COMMON_KNOWLEDGE_PATH)
        self.documents_path = Path(RAG_DOCUMENTS_PATH)
        self.common_knowledge_path.mkdir(parents=True, exist_ok=True)
        self.documents_path.mkdir(parents=True, exist_ok=True)
    
    # ========== FILE VALIDATION AND UTILITIES ==========
    
    def is_valid_file(self, file_name: str, file_size: int) -> Tuple[bool, str]:
        """Validate file name and size"""
        if not file_name or file_name.strip() == "":
            return False, "Invalid file name"
        
        if not any(file_name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
            return False, f"Unsupported format. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        
        max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            actual_mb = file_size / (1024 * 1024)
            return False, f"File is {actual_mb:.1f}MB. Max size: {MAX_FILE_SIZE_MB}MB"
        
        if file_size == 0:
            return False, "File is empty"
        
        return True, ""
    
    def format_file_size(self, file_size: int) -> str:
        """Format file size in human readable format"""
        if file_size < 1024:
            return f"{file_size} B"
        elif file_size < 1024 * 1024:
            return f"{file_size / 1024:.1f} KB"
        else:
            return f"{file_size / (1024 * 1024):.1f} MB"
    
    def get_file_type(self, file_path: Path) -> str:
        """Get file type description"""
        file_ext = file_path.suffix.upper().replace(".", "")
        return f"{file_ext} Document" if file_ext else "Document"
    
    def get_user_display_name(self, email: str) -> str:
        """Get actual user display name from database"""
        try:
            if IS_PRODUCTION:
                result = self.supabase.table("users")\
                    .select("name")\
                    .eq("email", email)\
                    .execute()
                
                if result.data and result.data[0].get("name"):
                    return result.data[0]["name"]
            
            return email.split('@')[0].replace('.', ' ').replace('-', ' ').title()
        except Exception as e:
            print(f"Error getting user name: {e}")
            return email.split('@')[0].replace('.', ' ').title()
    
    # ========== COMMON KNOWLEDGE OPERATIONS ==========
    
    def upload_common_knowledge_files(self, files, uploaded_by: str) -> Tuple[List[List[Any]], str, List[str]]:
        """Upload files to common knowledge repository"""
        if not files:
            return [], "No files selected", []

        file_paths = self._extract_file_paths(files)
        if not file_paths:
            return [], "No valid file paths found", []

        uploaded_count = 0
        total_chunks = 0
        errors = []
        status_updates = []

        for i, file_path in enumerate(file_paths):
            result = self._process_common_knowledge_upload(file_path, uploaded_by, i + 1, len(file_paths))
            
            if result["success"]:
                uploaded_count += 1
                total_chunks += result["chunks"]
                status_updates.extend(result["messages"])
            else:
                errors.extend(result["errors"])
                status_updates.extend(result["messages"])

        final_status = self._build_status_message(status_updates, uploaded_count, total_chunks, errors, "uploaded")
        files_list = self.get_common_knowledge_file_list()
        choices = [row[0] for row in files_list] if files_list else []
        
        return files_list, final_status, choices

    def delete_common_knowledge_files(self, selected_files: List[str]) -> Tuple[List[List[Any]], str, List[str]]:
        """Delete files from common knowledge repository"""
        if not selected_files:
            return [], "No files selected", []
        
        deleted_count = 0
        errors = []
        status_updates = []

        for i, file_name in enumerate(selected_files):
            status_updates.append(f"Deleting {i+1}/{len(selected_files)}: {file_name}")
            
            success, error_msg = self._delete_common_knowledge_file(file_name)
            if success:
                deleted_count += 1
                status_updates.append(f"✅ Deleted: {file_name}")
            else:
                errors.append(f"{file_name}: {error_msg}")

        final_status = self._build_status_message(status_updates, deleted_count, 0, errors, "deleted")
        files_list = self.get_common_knowledge_file_list()
        choices = [row[0] for row in files_list] if files_list else []
        
        return files_list, final_status, choices
    
    def get_common_knowledge_file_list(self, search_term: str = "") -> List[List[Any]]:
        """Get formatted file list for common knowledge repository"""
        files = []
        
        if USE_S3_STORAGE:
            # Get files from S3
            s3_files = s3_storage.list_common_knowledge_files()
            for file_info in s3_files:
                file_row = self._create_common_knowledge_file_row_s3(file_info)
                if file_row and self._matches_search(file_row, search_term):
                    files.append(file_row)
        else:
            # Get local files
            if self.common_knowledge_path.exists():
                for file_path in self.common_knowledge_path.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                        file_row = self._create_common_knowledge_file_row_local(file_path)
                        if file_row and self._matches_search(file_row, search_term):
                            files.append(file_row)
        
        return files
    
    def get_common_knowledge_file_list_for_users(self) -> List[List[Any]]:
        """Get user-friendly file list for regular users (simplified view)"""
        files = []
        
        if USE_S3_STORAGE:
            # Get files from S3
            s3_files = s3_storage.list_common_knowledge_files()
            for file_info in s3_files:
                files.append([
                    file_info['file_name'],
                    self.format_file_size(file_info['file_size']),
                    self.get_file_type(Path(file_info['file_name'])),
                    file_info['last_modified'].strftime("%Y-%m-%d") if hasattr(file_info['last_modified'], 'strftime') else str(file_info['last_modified'])[:10]
                ])
        else:
            # Get local files
            if self.common_knowledge_path.exists():
                for file_path in self.common_knowledge_path.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                        try:
                            stat = file_path.stat()
                            files.append([
                                file_path.name,
                                self.format_file_size(stat.st_size),
                                self.get_file_type(file_path),
                                datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
                            ])
                        except Exception as e:
                            print(f"Error reading file {file_path}: {e}")
                            continue
        
        return files

    def reindex_common_knowledge_pending_files(self) -> str:
        """Re-index files that are not yet indexed"""
        try:
            from rag_service import rag_service
            
            files = self.get_common_knowledge_file_list()
            pending_files = [f for f in files if f[4] == "⏳ Pending"]  # Status is at index 4
            
            if not pending_files:
                return "✅ All files already indexed"
            
            reindexed, pending_count, errors = rag_service.reindex_common_knowledge_pending_files()
            
            result = f"📚 Re-indexing Summary:\n"
            result += f"• Files processed: {reindexed}/{pending_count}\n"
            
            if reindexed > 0:
                result += f"✅ Successfully indexed: {reindexed} files\n"
            
            if errors:
                result += f"\n⚠️ ERRORS ({len(errors)}):\n" + "\n".join([f"• {error}" for error in errors])
            
            return result
            
        except Exception as e:
            return f"Error re-indexing: {str(e)}"
    
    # ========== USER FILE OPERATIONS ==========
    
    def get_user_documents_path(self, user_email: str) -> Path:
        """Get user-specific documents directory (for local temp processing)"""
        user_dir = self.documents_path / user_email.replace("@", "_").replace(".", "_")
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    
    def upload_user_files(self, user_email: str, files) -> Tuple[List[List[Any]], str, List[str]]:
        """Upload files for specific user"""
        if not files or not user_email:
            return [], "No files selected or user not specified", []

        file_paths = self._extract_file_paths(files)
        if not file_paths:
            return [], "No valid file paths found", []

        uploaded_count = 0
        total_chunks = 0
        errors = []
        status_updates = []

        for i, file_path in enumerate(file_paths):
            result = self._process_user_file_upload(user_email, file_path, i + 1, len(file_paths))
            
            if result["success"]:
                uploaded_count += 1
                total_chunks += result["chunks"]
                status_updates.extend(result["messages"])
            else:
                errors.extend(result["errors"])
                status_updates.extend(result["messages"])

        final_status = self._build_status_message(
            status_updates, uploaded_count, total_chunks, errors, "uploaded", user_email
        )
        files_list = self.get_user_file_list(user_email)
        choices = [row[0] for row in files_list] if files_list else []
        
        return files_list, final_status, choices
    
    def delete_user_files(self, user_email: str, selected_files: List[str]) -> Tuple[List[List[Any]], str, List[str]]:
        """Delete files for specific user"""
        if not selected_files or not user_email:
            return [], "No files selected or user not specified", []
        
        deleted_count = 0
        errors = []
        status_updates = []

        for i, file_name in enumerate(selected_files):
            status_updates.append(f"Deleting {i+1}/{len(selected_files)}: {file_name}")
            
            success, error_msg = self._delete_user_file(user_email, file_name)
            if success:
                deleted_count += 1
                status_updates.append(f"✅ Deleted: {file_name}")
            else:
                errors.append(f"{file_name}: {error_msg}")

        final_status = self._build_status_message(
            status_updates, deleted_count, 0, errors, "deleted", user_email
        )
        files_list = self.get_user_file_list(user_email)
        choices = [row[0] for row in files_list] if files_list else []
        
        return files_list, final_status, choices
    
    def get_user_file_list(self, user_email: str, search_term: str = "") -> List[List[Any]]:
        """Get formatted file list for specific user"""
        if not user_email:
            return []
        
        files = []
        
        if USE_S3_STORAGE:
            # Get files from S3
            s3_files = s3_storage.list_user_files(user_email)
            for file_info in s3_files:
                file_row = self._create_user_file_row_s3(file_info, user_email)
                if file_row and self._matches_search(file_row, search_term):
                    files.append(file_row)
        else:
            # Get local files
            user_docs_path = self.get_user_documents_path(user_email)
            for file_path in user_docs_path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    file_row = self._create_user_file_row_local(file_path, user_email)
                    if file_row and self._matches_search(file_row, search_term):
                        files.append(file_row)
        
        return files
    
    def reindex_user_pending_files(self, user_email: str) -> str:
        """Re-index user files that are not yet indexed"""
        try:
            from rag_service import rag_service
            
            reindexed, pending_count, errors = rag_service.reindex_user_pending_files(user_email)
            
            result = f"📚 User Re-indexing Summary for {user_email}:\n"
            result += f"• Files processed: {reindexed}/{pending_count}\n"
            
            if reindexed > 0:
                result += f"✅ Successfully indexed: {reindexed} files\n"
            
            if errors:
                result += f"\n⚠️ ERRORS ({len(errors)}):\n" + "\n".join([f"• {error}" for error in errors])
            
            return result
            
        except Exception as e:
            return f"Error re-indexing user files: {str(e)}"
    
    # ========== HELPER METHODS ==========
    
    def _extract_file_paths(self, files) -> List[str]:
        """Extract file paths from various input formats"""
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
        return file_paths
    
    def _process_common_knowledge_upload(self, file_path: str, uploaded_by: str, current: int, total: int) -> Dict:
        """Process single common knowledge file upload"""
        if not file_path or not os.path.exists(file_path):
            return {"success": False, "chunks": 0, "messages": [], "errors": [f"File not found: {file_path}"]}
        
        file_name = os.path.basename(file_path)
        messages = [f"Processing {current}/{total}: {file_name}"]
        
        try:
            file_size = os.path.getsize(file_path)
            is_valid, error_msg = self.is_valid_file(file_name, file_size)
            if not is_valid:
                return {"success": False, "chunks": 0, "messages": messages, "errors": [f"{file_name}: {error_msg}"]}
            
            # Check if file already exists
            if self._file_exists_in_common_knowledge(file_name):
                return {"success": False, "chunks": 0, "messages": messages, "errors": [f"{file_name}: File already exists"]}
            
            # Upload file to storage
            if USE_S3_STORAGE:
                success = s3_storage.upload_common_knowledge_file(file_path, file_name)
            else:
                target_path = self.common_knowledge_path / file_name
                shutil.copy2(file_path, target_path)
                success = target_path.exists()
            
            if not success:
                return {"success": False, "chunks": 0, "messages": messages, "errors": [f"{file_name}: Upload failed"]}
            
            messages.append(f"✅ Uploaded: {file_name}")
            
            # Store in database
            if IS_PRODUCTION:
                self._store_file_in_database(file_name, file_size, uploaded_by)
            
            # Index the file
            chunks_count = self._index_file(file_name, messages, is_common=True)
            
            return {"success": True, "chunks": chunks_count, "messages": messages, "errors": []}
            
        except Exception as e:
            return {"success": False, "chunks": 0, "messages": messages, "errors": [f"{file_name}: {str(e)}"]}
    
    def _process_user_file_upload(self, user_email: str, file_path: str, current: int, total: int) -> Dict:
        """Process single user file upload"""
        if not file_path or not os.path.exists(file_path):
            return {"success": False, "chunks": 0, "messages": [], "errors": [f"File not found: {file_path}"]}
        
        file_name = os.path.basename(file_path)
        messages = [f"Processing {current}/{total}: {file_name}"]
        
        try:
            file_size = os.path.getsize(file_path)
            is_valid, error_msg = self.is_valid_file(file_name, file_size)
            if not is_valid:
                return {"success": False, "chunks": 0, "messages": messages, "errors": [f"{file_name}: {error_msg}"]}
            
            # Check if file already exists
            if self._file_exists_for_user(user_email, file_name):
                return {"success": False, "chunks": 0, "messages": messages, "errors": [f"{file_name}: File already exists for user"]}
            
            # Upload file to storage
            if USE_S3_STORAGE:
                success = s3_storage.upload_user_file(user_email, file_path, file_name)
            else:
                user_docs_path = self.get_user_documents_path(user_email)
                target_path = user_docs_path / file_name
                shutil.copy2(file_path, target_path)
                success = target_path.exists()
            
            if not success:
                return {"success": False, "chunks": 0, "messages": messages, "errors": [f"{file_name}: Upload failed"]}
            
            messages.append(f"✅ Uploaded: {file_name}")
            
            # Index the file
            chunks_count = self._index_user_file(user_email, file_name, messages)
            
            return {"success": True, "chunks": chunks_count, "messages": messages, "errors": []}
            
        except Exception as e:
            return {"success": False, "chunks": 0, "messages": messages, "errors": [f"{file_name}: {str(e)}"]}
    
    def _delete_common_knowledge_file(self, file_name: str) -> Tuple[bool, str]:
        """Delete single common knowledge file"""
        try:
            # Remove from vector store first
            from rag_service import rag_service
            rag_service.remove_common_knowledge_document(file_name)
            
            # Delete from storage
            if USE_S3_STORAGE:
                success = s3_storage.delete_common_knowledge_file(file_name)
            else:
                file_path = self.common_knowledge_path / file_name
                if file_path.exists():
                    file_path.unlink()
                    success = True
                else:
                    success = False
            
            if not success:
                return False, "Storage deletion failed"
            
            # Delete from database
            if IS_PRODUCTION:
                try:
                    self.supabase.table("common_knowledge_documents")\
                        .delete()\
                        .eq("file_name", file_name)\
                        .execute()
                except Exception as db_error:
                    print(f"Warning: Database cleanup failed for {file_name}: {db_error}")
            
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    def _delete_user_file(self, user_email: str, file_name: str) -> Tuple[bool, str]:
        """Delete single user file"""
        try:
            # Delete from storage
            if USE_S3_STORAGE:
                success = s3_storage.delete_user_file(user_email, file_name)
            else:
                user_docs_path = self.get_user_documents_path(user_email)
                file_path = user_docs_path / file_name
                if file_path.exists():
                    file_path.unlink()
                    success = True
                else:
                    success = False
            
            return (True, "") if success else (False, "File not found or deletion failed")
                
        except Exception as e:
            return False, str(e)
    
    def _file_exists_in_common_knowledge(self, file_name: str) -> bool:
        """Check if file exists in common knowledge storage"""
        if USE_S3_STORAGE:
            s3_files = s3_storage.list_common_knowledge_files()
            return any(f['file_name'] == file_name for f in s3_files)
        else:
            return (self.common_knowledge_path / file_name).exists()
    
    def _file_exists_for_user(self, user_email: str, file_name: str) -> bool:
        """Check if file exists for user"""
        if USE_S3_STORAGE:
            user_files = s3_storage.list_user_files(user_email)
            return any(f['file_name'] == file_name for f in user_files)
        else:
            user_docs_path = self.get_user_documents_path(user_email)
            return (user_docs_path / file_name).exists()
    
    def _create_common_knowledge_file_row_s3(self, file_info: Dict) -> Optional[list]:
        """Create a row for S3 common knowledge files"""
        try:
            from rag_service import rag_service

            file_name = file_info['file_name']
            file_size = file_info['file_size']
            last_modified = file_info['last_modified']
            
            chunks_count = rag_service.get_file_chunks_count(file_name, is_common=True)
            status = "✅ Indexed" if chunks_count > 0 else "⏳ Pending"
            
            upload_date = last_modified.strftime("%Y-%m-%d") if hasattr(last_modified, 'strftime') else str(last_modified)[:10]

            # Get file URL
            file_url = s3_storage.get_common_knowledge_file_url(file_name)
            actions = self._create_file_actions(file_url)

            # Uploader name from metadata
            metadata = file_info.get('metadata', {})
            uploader_name = "System"
            if 'uploaded_by' in metadata:
                uploader_name = self.get_user_display_name(metadata['uploaded_by'])

            return [file_name, self.format_file_size(file_size), self.get_file_type(Path(file_name)), 
                   chunks_count, status, upload_date, uploader_name, actions]

        except Exception as e:
            print(f"Error creating S3 file row {file_info}: {e}")
            return None
    
    def _create_common_knowledge_file_row_local(self, file_path: Path) -> Optional[list]:
        """Create a row for local common knowledge files"""
        try:
            from rag_service import rag_service

            stat = file_path.stat()
            file_size = stat.st_size
            chunks_count = rag_service.get_file_chunks_count(file_path.name, is_common=True)
            status = "✅ Indexed" if chunks_count > 0 else "⏳ Pending"
            upload_date = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")

            file_url = f"/docs/{file_path.name}"
            actions = self._create_file_actions(file_url)

            uploader_name = "System"
            if IS_PRODUCTION:
                try:
                    result = self.supabase.table("common_knowledge_documents") \
                        .select("uploaded_by") \
                        .eq("file_name", file_path.name) \
                        .execute()
                    if result.data and result.data[0].get("uploaded_by"):
                        uploader_name = self.get_user_display_name(result.data[0]["uploaded_by"])
                except Exception:
                    pass

            return [file_path.name, self.format_file_size(file_size), self.get_file_type(file_path), 
                   chunks_count, status, upload_date, uploader_name, actions]

        except Exception as e:
            print(f"Error reading local file {file_path}: {e}")
            return None
    
    def _create_user_file_row_s3(self, file_info: Dict, user_email: str) -> Optional[List[Any]]:
        """Create file row for S3 user files"""
        try:
            from rag_service import rag_service
            
            file_name = file_info['file_name']
            file_size = file_info['file_size']
            last_modified = file_info['last_modified']
            
            # Get chunks count from user vector store
            chunks_count = self._get_user_file_chunks_count(user_email, file_name)
            status = "✅ Indexed" if chunks_count > 0 else "⏳ Pending"
            upload_date = last_modified.strftime("%Y-%m-%d") if hasattr(last_modified, 'strftime') else str(last_modified)[:10]
            
            user_display = self.get_user_display_name(user_email)
            file_url = s3_storage.get_user_file_url(user_email, file_name)
            actions = self._create_file_actions(file_url)
            
            return [file_name, self.format_file_size(file_size), self.get_file_type(Path(file_name)), 
                   chunks_count, status, upload_date, user_display, actions]
            
        except Exception as e:
            print(f"Error creating S3 user file row {file_info}: {e}")
            return None
    
    def _create_user_file_row_local(self, file_path: Path, user_email: str) -> Optional[List[Any]]:
        """Create file row for local user files"""
        try:
            stat = file_path.stat()
            file_size = stat.st_size
            
            chunks_count = self._get_user_file_chunks_count(user_email, file_path.name)
            status = "✅ Indexed" if chunks_count > 0 else "⏳ Pending"
            upload_date = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
            
            user_display = self.get_user_display_name(user_email)
            user_dir = user_email.replace("@", "_").replace(".", "_")
            file_url = f"/user_docs/{user_dir}/{file_path.name}"
            actions = self._create_file_actions(file_url)
            
            return [file_path.name, self.format_file_size(file_size), self.get_file_type(file_path), 
                   chunks_count, status, upload_date, user_display, actions]
            
        except Exception as e:
            print(f"Error reading local user file {file_path}: {e}")
            return None
    
    def _get_user_file_chunks_count(self, user_email: str, file_name: str) -> int:
        """Get chunks count for user file"""
        try:
            from rag_service import rag_service
            vectorstore = rag_service.get_user_vectorstore(user_email)
            collection = vectorstore._collection
            existing_results = collection.get(where={"file_name": file_name})
            return len(existing_results['ids']) if existing_results and existing_results['ids'] else 0
        except Exception:
            return 0
    
    def _create_file_actions(self, file_url: Optional[str]) -> str:
        """Create actions HTML for file row"""
        if file_url:
            return (
                f'<a href="{file_url}" target="_blank" style="color: #3b82f6; text-decoration: none; font-weight: 500;">👁 View</a> '
                f'<span style="color: #6b7280;">|</span> '
                f'<a href="{file_url}" download style="color: #059669; text-decoration: none; font-weight: 500;">💾 Download</a>'
            )
        else:
            return '<span style="color: #ef4444;">❌ Unavailable</span>'
    
    def _store_file_in_database(self, file_name: str, file_size: int, uploaded_by: str):
        """Store file metadata in database"""
        try:
            doc_data = {
                "file_name": file_name,
                "file_path": f"s3://{s3_storage.bucket_name}/{s3_storage.common_prefix}{file_name}" if USE_S3_STORAGE else str(Path(file_name)),
                "file_size": file_size,
                "file_hash": "",  # Skip hash for now
                "uploaded_by": uploaded_by,
                "is_common_knowledge": True,
                "storage_type": "s3" if USE_S3_STORAGE else "local"
            }
            self.supabase.table("common_knowledge_documents").insert(doc_data).execute()
        except Exception as db_error:
            print(f"Warning: Database update failed for {file_name}: {db_error}")
    
    def _index_file(self, file_name: str, messages: List[str], is_common: bool = True) -> int:
        """Index a file and return chunks count"""
        try:
            from rag_service import rag_service
            
            if is_common:
                index_success, index_msg, chunks_count = rag_service.index_common_knowledge_document(file_name)
            else:
                return 0
            
            if index_success:
                messages.append(f"📚 Indexed: {file_name} ({chunks_count} chunks)")
                return chunks_count
            else:
                messages.append(f"⚠️ Indexing failed: {file_name} - {index_msg}")
                return 0
                
        except Exception as index_error:
            messages.append(f"⚠️ Indexing error: {file_name} - {str(index_error)}")
            return 0
    
    def _index_user_file(self, user_email: str, file_name: str, messages: List[str]) -> int:
        """Index a user file and return chunks count"""
        try:
            from rag_service import rag_service
            
            index_success, index_msg, chunks_count = rag_service.index_user_document(user_email, file_name)
            
            if index_success:
                messages.append(f"📚 Indexed: {file_name} ({chunks_count} chunks)")
                return chunks_count
            else:
                messages.append(f"⚠️ Indexing failed: {file_name} - {index_msg}")
                return 0
                
        except Exception as index_error:
            messages.append(f"⚠️ Indexing error: {file_name} - {str(index_error)}")
            return 0
    
    def _matches_search(self, file_row: List[Any], search_term: str) -> bool:
        """Check if file row matches search term"""
        if not search_term:
            return True
        
        search_lower = search_term.lower()
        searchable_text = " ".join([
            str(cell).lower() for cell in file_row[:3]  # Name, Size, Type
        ] + [file_row[4].lower()])  # Status
        
        return search_lower in searchable_text
    
    def _build_status_message(self, status_updates: List[str], count: int, chunks: int, 
                            errors: List[str], operation: str, user_email: str = None) -> str:
        """Build comprehensive status message"""
        final_status = "\n".join(status_updates)
        
        if count > 0:
            user_info = f" for {user_email}" if user_email else ""
            if operation == "uploaded" and chunks > 0:
                final_status += f"\n\n🎉 COMPLETED: {count} files {operation}{user_info} with {chunks} chunks"
            else:
                final_status += f"\n\n🎉 COMPLETED: {count} files {operation}{user_info}"
        
        if errors:
            final_status += f"\n\n⚠️ ERRORS:\n" + "\n".join([f"• {error}" for error in errors])
        
        return final_status

# Global service instances
enhanced_file_service = EnhancedFileService()

# Backward compatibility aliases
common_knowledge_service = enhanced_file_service
user_file_service = enhanced_file_service