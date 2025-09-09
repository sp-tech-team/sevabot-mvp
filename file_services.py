# file_services.py - File management with local/cloud support
import os
import hashlib
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

from config import (
    COMMON_KNOWLEDGE_PATH, RAG_DOCUMENTS_PATH, 
    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, IS_PRODUCTION
)
from constants import SUPPORTED_EXTENSIONS, MAX_FILE_SIZE_MB, ERROR_MESSAGES
from supabase import create_client
from rag_service import rag_service

class CommonKnowledgeService:
    """Common knowledge file management with local/cloud support"""
    
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        self.common_knowledge_path = Path(COMMON_KNOWLEDGE_PATH)
        self.common_knowledge_path.mkdir(parents=True, exist_ok=True)
    
    def get_file_hash(self, file_path: Path) -> str:
        """Generate MD5 hash of file"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5()
                for chunk in iter(lambda: f.read(4096), b""):
                    file_hash.update(chunk)
                return file_hash.hexdigest()
        except Exception as e:
            print(f"Error generating hash for {file_path}: {e}")
            return ""
    
    def is_valid_file(self, file_name: str, file_size: int) -> Tuple[bool, str]:
        """Validate file name and size"""
        if not file_name or file_name.strip() == "":
            return False, "Invalid file name"
        
        file_ext = Path(file_name).suffix.lower()
        if not any(file_name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
            return False, f"Unsupported format. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        
        max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            actual_mb = file_size / (1024 * 1024)
            return False, f"File is {actual_mb:.1f}MB. Max size: {MAX_FILE_SIZE_MB}MB"
        
        if file_size == 0:
            return False, "File is empty"
        
        return True, ""
    
    def upload_files(self, files, uploaded_by: str) -> Tuple[List[List[Any]], str, List[str]]:
        """Upload files to common knowledge repository"""
        if not files:
            return [], "No files selected", []

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
                return [], "No valid file paths found", []

            uploaded_count = 0
            total_chunks = 0
            errors = []
            status_updates = []

            for i, file_path in enumerate(file_paths):
                if not file_path or not os.path.exists(file_path):
                    errors.append(f"File not found: {file_path}")
                    continue
                    
                file_name = os.path.basename(file_path)
                try:
                    file_size = os.path.getsize(file_path)
                except OSError as e:
                    errors.append(f"Cannot access {file_name}: {str(e)}")
                    continue
                
                status_updates.append(f"Processing {i+1}/{len(file_paths)}: {file_name}")
                
                # Validate file
                is_valid, error_msg = self.is_valid_file(file_name, file_size)
                if not is_valid:
                    errors.append(f"{file_name}: {error_msg}")
                    continue
                
                # Get target path
                target_path = self.common_knowledge_path / file_name
                
                # Check if file already exists
                if target_path.exists():
                    errors.append(f"{file_name}: File already exists")
                    continue
                
                try:
                    # Copy file
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, target_path)
                    
                    # Verify copy
                    if not target_path.exists():
                        errors.append(f"{file_name}: Copy failed")
                        continue
                    
                    uploaded_count += 1
                    status_updates.append(f"✅ Uploaded: {file_name}")
                    
                    # Store in database only in production
                    if IS_PRODUCTION:
                        try:
                            file_hash = self.get_file_hash(target_path)
                            doc_data = {
                                "file_name": file_name,
                                "file_path": str(target_path.relative_to(self.common_knowledge_path)),
                                "file_size": file_size,
                                "file_hash": file_hash,
                                "uploaded_by": uploaded_by,
                                "is_common_knowledge": True
                            }
                            self.supabase.table("common_knowledge_documents").insert(doc_data).execute()
                        except Exception as db_error:
                            print(f"Warning: Database update failed for {file_name}: {db_error}")
                    
                    # Index the file
                    try:
                        index_success, index_msg, chunks_count = rag_service.index_common_knowledge_document(file_name)
                        if index_success:
                            total_chunks += chunks_count
                            status_updates.append(f"📚 Indexed: {file_name} ({chunks_count} chunks)")
                        else:
                            errors.append(f"{file_name}: {index_msg}")
                    except Exception as index_error:
                        errors.append(f"{file_name}: Indexing error - {str(index_error)}")
                        
                except Exception as e:
                    errors.append(f"{file_name}: {str(e)}")

            final_status = "\n".join(status_updates)
            if uploaded_count > 0:
                final_status += f"\n\n🎉 COMPLETED: {uploaded_count} files uploaded with {total_chunks} chunks"
            if errors:
                final_status += f"\n\n⚠️ ERRORS:\n" + "\n".join([f"• {error}" for error in errors])

            files_list = self.get_file_list()
            choices = [row[0] for row in files_list] if files_list else []
            
            return files_list, final_status, choices
            
        except Exception as e:
            return [], f"Upload error: {str(e)}", []

    def delete_files(self, selected_files: List[str]) -> Tuple[List[List[Any]], str, List[str]]:
        """Delete files from common knowledge repository"""
        if not selected_files:
            return [], "No files selected", []
        
        try:
            deleted_count = 0
            errors = []
            status_updates = []

            for i, file_name in enumerate(selected_files):
                status_updates.append(f"Deleting {i+1}/{len(selected_files)}: {file_name}")
                
                try:
                    # Remove from vector store
                    rag_service.remove_common_knowledge_document(file_name)
                    
                    # Delete from filesystem
                    file_path = self.common_knowledge_path / file_name
                    if file_path.exists():
                        file_path.unlink()
                        deleted_count += 1
                        status_updates.append(f"✅ Deleted: {file_name}")
                    else:
                        errors.append(f"{file_name}: File not found")
                    
                    # Delete from database only in production
                    if IS_PRODUCTION:
                        try:
                            self.supabase.table("common_knowledge_documents")\
                                .delete()\
                                .eq("file_name", file_name)\
                                .execute()
                        except Exception as db_error:
                            print(f"Warning: Database cleanup failed for {file_name}: {db_error}")
                        
                except Exception as e:
                    errors.append(f"{file_name}: {str(e)}")

            final_status = "\n".join(status_updates)
            if deleted_count > 0:
                final_status += f"\n\n🎉 COMPLETED: {deleted_count} files deleted"
            if errors:
                final_status += f"\n\n⚠️ ERRORS:\n" + "\n".join([f"• {error}" for error in errors])

            files_list = self.get_file_list()
            choices = [row[0] for row in files_list] if files_list else []
            
            return files_list, final_status, choices
            
        except Exception as e:
            return [], f"Delete error: {str(e)}", []
    
    def get_file_list(self, search_term: str = "") -> List[List[Any]]:
        """Get formatted file list with search - combines local and cloud data"""
        try:
            files = []
            
            # Get local files
            if self.common_knowledge_path.exists():
                for file_path in self.common_knowledge_path.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                        try:
                            stat = file_path.stat()
                            file_size = stat.st_size
                            
                            # Format file size
                            if file_size < 1024:
                                size_str = f"{file_size} B"
                            elif file_size < 1024 * 1024:
                                size_str = f"{file_size / 1024:.1f} KB"
                            else:
                                size_str = f"{file_size / (1024 * 1024):.1f} MB"
                            
                            # Get file extension for type
                            file_ext = file_path.suffix.upper().replace(".", "")
                            file_type = f"{file_ext} Document" if file_ext else "Document"
                            
                            # Get chunks count
                            chunks_count = rag_service.get_file_chunks_count(file_path.name)
                            status = "✅ Indexed" if chunks_count > 0 else "⏳ Pending"
                            
                            # Upload date
                            upload_date = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
                            
                            file_row = [
                                file_path.name,
                                size_str,
                                file_type,
                                chunks_count,
                                status,
                                upload_date,
                                "Local"
                            ]
                            
                            # Apply search filter
                            if search_term:
                                search_lower = search_term.lower()
                                searchable_text = " ".join([
                                    file_path.name.lower(),
                                    file_type.lower(),
                                    status.lower()
                                ])
                                if search_lower not in searchable_text:
                                    continue
                            
                            files.append(file_row)
                            
                        except Exception as e:
                            print(f"Error reading local file {file_path}: {e}")
                            continue
            
            # Get cloud files if in production
            if IS_PRODUCTION:
                try:
                    result = self.supabase.table("common_knowledge_documents")\
                        .select("*")\
                        .order("uploaded_at", desc=True)\
                        .execute()
                    
                    local_files = {row[0] for row in files}  # Get local file names
                    
                    if result.data:
                        for file_info in result.data:
                            # Skip if we already have this file locally
                            if file_info["file_name"] in local_files:
                                continue
                            
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
                            
                            chunks_count = file_info.get("chunks_count", 0)
                            status = "✅ Indexed" if chunks_count > 0 else "⏳ Pending"
                            
                            file_row = [
                                file_info["file_name"],
                                size_str,
                                file_type,
                                chunks_count,
                                status,
                                file_info["uploaded_at"][:10],
                                file_info.get("uploaded_by", "Cloud")
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
                            
                            files.append(file_row)
                            
                except Exception as e:
                    print(f"Error getting cloud files: {e}")
            
            return files
            
        except Exception as e:
            print(f"Error getting file list: {e}")
            return []
    
    def get_file_list_for_users(self) -> List[List[Any]]:
        """Get user-friendly file list for regular users"""
        try:
            files = []
            
            # Get local files
            if self.common_knowledge_path.exists():
                for file_path in self.common_knowledge_path.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                        try:
                            stat = file_path.stat()
                            file_size = stat.st_size
                            
                            # Format file size
                            if file_size < 1024:
                                size_str = f"{file_size} B"
                            elif file_size < 1024 * 1024:
                                size_str = f"{file_size / 1024:.1f} KB"
                            else:
                                size_str = f"{file_size / (1024 * 1024):.1f} MB"
                            
                            # Get file extension for type
                            file_ext = file_path.suffix.upper().replace(".", "")
                            file_type = f"{file_ext} Document" if file_ext else "Document"
                            
                            # Upload date
                            upload_date = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
                            
                            files.append([
                                file_path.name,
                                size_str,
                                file_type,
                                upload_date
                            ])
                            
                        except Exception as e:
                            print(f"Error reading file {file_path}: {e}")
                            continue
            
            return files
            
        except Exception as e:
            print(f"Error getting user file list: {e}")
            return []
    
    def reindex_pending_files(self) -> str:
        """Re-index files that are not yet indexed"""
        try:
            files = self.get_file_list()
            pending_files = [f for f in files if f[4] == "⏳ Pending"]  # Status is at index 4
            
            if not pending_files:
                return "✅ All files already indexed"
            
            reindexed = 0
            errors = []
            
            for file_info in pending_files:
                file_name = file_info[0]
                try:
                    success, msg, chunks = rag_service.index_common_knowledge_document(file_name)
                    if success:
                        reindexed += 1
                    else:
                        errors.append(f"{file_name}: {msg}")
                except Exception as e:
                    errors.append(f"{file_name}: {str(e)}")
            
            result = f"📚 Re-indexing Summary:\n"
            result += f"• Files processed: {reindexed}/{len(pending_files)}"
            
            if reindexed > 0:
                result += f"\n✅ Successfully indexed: {reindexed} files"
            
            if errors:
                result += f"\n\n⚠️ ERRORS ({len(errors)}):\n" + "\n".join([f"• {error}" for error in errors])
            
            return result
            
        except Exception as e:
            return f"Error re-indexing: {str(e)}"

class UserFileService:
    """Per-user file management"""
    
    def __init__(self):
        self.documents_path = Path(RAG_DOCUMENTS_PATH)
        self.documents_path.mkdir(parents=True, exist_ok=True)
    
    def get_user_documents_path(self, user_email: str) -> Path:
        """Get user-specific documents directory"""
        user_dir = self.documents_path / user_email.replace("@", "_").replace(".", "_")
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    
    def upload_files_for_user(self, user_email: str, files) -> Tuple[List[List[Any]], str, List[str]]:
        """Upload files for specific user"""
        if not files or not user_email:
            return [], "No files selected or user not specified", []

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
                return [], "No valid file paths found", []

            user_docs_path = self.get_user_documents_path(user_email)
            uploaded_count = 0
            errors = []
            status_updates = []

            for i, file_path in enumerate(file_paths):
                if not file_path or not os.path.exists(file_path):
                    errors.append(f"File not found: {file_path}")
                    continue
                    
                file_name = os.path.basename(file_path)
                target_path = user_docs_path / file_name
                status_updates.append(f"Processing {i+1}/{len(file_paths)}: {file_name}")
                
                try:
                    # Check if file already exists
                    if target_path.exists():
                        errors.append(f"{file_name}: File already exists for user")
                        continue
                    
                    # Copy file to user directory
                    shutil.copy2(file_path, target_path)
                    uploaded_count += 1
                    status_updates.append(f"✅ Uploaded: {file_name}")
                        
                except Exception as e:
                    errors.append(f"{file_name}: {str(e)}")

            final_status = "\n".join(status_updates)
            if uploaded_count > 0:
                final_status += f"\n\n🎉 COMPLETED: {uploaded_count} files uploaded for {user_email}"
            if errors:
                final_status += f"\n\n⚠️ ERRORS:\n" + "\n".join([f"• {error}" for error in errors])

            files_list = self.get_user_file_list(user_email)
            choices = [row[0] for row in files_list] if files_list else []
            
            return files_list, final_status, choices
            
        except Exception as e:
            return [], f"Upload error: {str(e)}", []
    
    def delete_user_files(self, user_email: str, selected_files: List[str]) -> Tuple[List[List[Any]], str, List[str]]:
        """Delete files for specific user"""
        if not selected_files or not user_email:
            return [], "No files selected or user not specified", []
        
        try:
            user_docs_path = self.get_user_documents_path(user_email)
            deleted_count = 0
            errors = []
            status_updates = []

            for i, file_name in enumerate(selected_files):
                status_updates.append(f"Deleting {i+1}/{len(selected_files)}: {file_name}")
                file_path = user_docs_path / file_name
                
                try:
                    if file_path.exists():
                        file_path.unlink()
                        deleted_count += 1
                        status_updates.append(f"✅ Deleted: {file_name}")
                    else:
                        errors.append(f"{file_name}: File not found")
                        
                except Exception as e:
                    errors.append(f"{file_name}: {str(e)}")

            final_status = "\n".join(status_updates)
            if deleted_count > 0:
                final_status += f"\n\n🎉 COMPLETED: {deleted_count} files deleted for {user_email}"
            if errors:
                final_status += f"\n\n⚠️ ERRORS:\n" + "\n".join([f"• {error}" for error in errors])

            files_list = self.get_user_file_list(user_email)
            choices = [row[0] for row in files_list] if files_list else []
            
            return files_list, final_status, choices
            
        except Exception as e:
            return [], f"Delete error: {str(e)}", []
    
    def get_user_file_list(self, user_email: str, search_term: str = "") -> List[List[Any]]:
        """Get formatted file list for specific user"""
        if not user_email:
            return []
        
        try:
            user_docs_path = self.get_user_documents_path(user_email)
            
            file_list = []
            for file_path in user_docs_path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    try:
                        stat = file_path.stat()
                        file_size = stat.st_size
                        
                        # Format file size
                        if file_size < 1024:
                            size_str = f"{file_size} B"
                        elif file_size < 1024 * 1024:
                            size_str = f"{file_size / 1024:.1f} KB"
                        else:
                            size_str = f"{file_size / (1024 * 1024):.1f} MB"
                        
                        # Get file extension for type
                        file_ext = file_path.suffix.upper().replace(".", "")
                        file_type = f"{file_ext} Document" if file_ext else "Document"
                        
                        # Upload date
                        upload_date = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
                        
                        file_row = [
                            file_path.name,
                            size_str,
                            file_type,
                            0,  # Chunks (not implemented for per-user yet)
                            "📄 Available",  # Status
                            upload_date,
                            user_email
                        ]
                        
                        # Apply search filter
                        if search_term:
                            search_lower = search_term.lower()
                            searchable_text = " ".join([
                                file_path.name.lower(),
                                file_type.lower()
                            ])
                            if search_lower not in searchable_text:
                                continue
                        
                        file_list.append(file_row)
                        
                    except Exception as e:
                        print(f"Error reading file {file_path}: {e}")
                        continue
            
            return file_list
            
        except Exception as e:
            print(f"Error getting user file list: {e}")
            return []

# Global service instances
common_knowledge_service = CommonKnowledgeService()
user_file_service = UserFileService()