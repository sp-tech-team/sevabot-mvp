# file_service.py - File management service
import os
import hashlib
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from config import RAG_DOCUMENTS_PATH, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from constants import SUPPORTED_EXTENSIONS, MAX_FILE_SIZE_MB, ERROR_MESSAGES
from supabase import create_client

class FileService:
    """Handles file operations for users"""
    
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        self.base_documents_path = Path(RAG_DOCUMENTS_PATH)
        self.base_documents_path.mkdir(exist_ok=True)
    
    def get_user_documents_path(self, user_email: str) -> Path:
        """Get user-specific documents directory"""
        user_folder = user_email.replace("@", "_").replace(".", "_")
        user_path = self.base_documents_path / user_folder
        user_path.mkdir(exist_ok=True)
        return user_path
    
    def get_file_hash(self, file_path: Path) -> str:
        """Generate MD5 hash of file"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def is_valid_file(self, file_name: str, file_size: int) -> Tuple[bool, str]:
        """Validate file name and size"""
        # Check extension
        if not any(file_name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
            return False, ERROR_MESSAGES["unsupported_format"]
        
        # Check size
        if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            return False, ERROR_MESSAGES["file_too_large"]
        
        return True, ""
    
    def upload_file(self, user_email: str, file_path: str) -> Tuple[bool, str]:
        """Upload file for user from temporary path"""
        try:
            # Get file info from source path
            source_path = Path(file_path)
            if not source_path.exists():
                return False, "Source file not found"
            
            file_name = source_path.name
            file_size = source_path.stat().st_size
            
            # Validate file
            is_valid, error_msg = self.is_valid_file(file_name, file_size)
            if not is_valid:
                return False, error_msg
            
            # Get user directory and target path
            user_path = self.get_user_documents_path(user_email)
            target_path = user_path / file_name
            
            # Check if file already exists in user directory
            if target_path.exists():
                # Compare file hashes to see if it's actually the same file
                existing_hash = self.get_file_hash(target_path)
                new_hash = self.get_file_hash(source_path)
                
                if existing_hash == new_hash:
                    return False, f"File '{file_name}' already exists with identical content."
                else:
                    return False, f"File '{file_name}' already exists. Please rename the file or delete the existing one."
            
            # Copy file from temp to user directory
            shutil.copy2(source_path, target_path)
            
            # Calculate hash of the copied file
            file_hash = self.get_file_hash(target_path)
            
            # Store in database
            doc_data = {
                "user_id": user_email,
                "file_name": file_name,
                "file_path": str(target_path.relative_to(self.base_documents_path)),
                "file_size": file_size,
                "file_hash": file_hash,
                "chunks_count": 0,  # Will be updated after indexing
                "uploaded_at": datetime.utcnow().isoformat(),
                "indexed_at": None
            }
            
            self.supabase.table("user_documents").insert(doc_data).execute()
            
            print(f"✅ File uploaded: {file_name} -> {target_path}")
            return True, f"✅ File '{file_name}' uploaded successfully"
            
        except Exception as e:
            print(f"Error uploading file: {e}")
            return False, ERROR_MESSAGES["upload_error"]
    
    def list_user_files(self, user_email: str) -> List[Dict]:
        """List all files for a user"""
        try:
            result = self.supabase.table("user_documents")\
                .select("*")\
                .eq("user_id", user_email)\
                .order("uploaded_at", desc=True)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error listing files: {e}")
            return []
    
    def delete_file(self, user_email: str, file_name: str) -> Tuple[bool, str]:
        """Delete a file for user"""
        try:
            # Get file info from database
            result = self.supabase.table("user_documents")\
                .select("*")\
                .eq("user_id", user_email)\
                .eq("file_name", file_name)\
                .execute()
            
            if not result.data:
                return False, f"File '{file_name}' not found"
            
            file_info = result.data[0]
            
            # Delete from filesystem
            user_path = self.get_user_documents_path(user_email)
            file_path = user_path / file_name
            
            if file_path.exists():
                file_path.unlink()
            
            # Delete from database
            self.supabase.table("user_documents")\
                .delete()\
                .eq("id", file_info["id"])\
                .execute()
            
            return True, f"✅ File '{file_name}' deleted successfully"
            
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False, ERROR_MESSAGES["delete_error"]
    
    def get_file_content(self, user_email: str, file_name: str) -> Optional[str]:
        """Get file content for processing"""
        try:
            user_path = self.get_user_documents_path(user_email)
            file_path = user_path / file_name
            
            if not file_path.exists():
                return None
            
            # For now, only handle text files directly
            if file_path.suffix.lower() in ['.txt', '.md']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            
            # For other files, return path for document loaders
            return str(file_path)
            
        except Exception as e:
            print(f"Error reading file content: {e}")
            return None
    
    def update_file_chunks_count(self, user_email: str, file_name: str, chunks_count: int):
        """Update chunks count after indexing"""
        try:
            self.supabase.table("user_documents")\
                .update({
                    "chunks_count": chunks_count,
                    "indexed_at": datetime.utcnow().isoformat()
                })\
                .eq("user_id", user_email)\
                .eq("file_name", file_name)\
                .execute()
        except Exception as e:
            print(f"Error updating chunks count: {e}")

# Global file service instance
file_service = FileService()