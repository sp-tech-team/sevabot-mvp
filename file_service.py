# file_service.py - Enhanced file management service
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
    """Enhanced file operations for users with better error handling"""
    
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
        """Generate MD5 hash of file with error handling"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5()
                # Read file in chunks for large files
                for chunk in iter(lambda: f.read(4096), b""):
                    file_hash.update(chunk)
                return file_hash.hexdigest()
        except Exception as e:
            print(f"Error generating hash for {file_path}: {e}")
            return ""
    
    def is_valid_file(self, file_name: str, file_size: int) -> Tuple[bool, str]:
        """Validate file name and size with detailed checks"""
        # Check if file name is valid
        if not file_name or file_name.strip() == "":
            return False, "Invalid file name"
        
        # Check extension
        file_ext = Path(file_name).suffix.lower()
        if not any(file_name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
            return False, f"{ERROR_MESSAGES['unsupported_format']} (found: {file_ext})"
        
        # Check size
        max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            actual_mb = file_size / (1024 * 1024)
            return False, f"File is {actual_mb:.1f}MB. {ERROR_MESSAGES['file_too_large']}"
        
        # Check for empty files
        if file_size == 0:
            return False, "File is empty"
        
        return True, ""
    
    def upload_file(self, user_email: str, file_path: str) -> Tuple[bool, str]:
        """Upload file with pre-validation to avoid storing unprocessable files"""
        try:
            # Validate source path
            source_path = Path(file_path)
            if not source_path.exists():
                return False, f"Source file not found: {file_path}"
            
            # Get file info
            file_name = source_path.name
            try:
                file_size = source_path.stat().st_size
            except OSError as e:
                return False, f"Cannot access file {file_name}: {str(e)}"
            
            # Validate file
            is_valid, error_msg = self.is_valid_file(file_name, file_size)
            if not is_valid:
                return False, error_msg
            
            # PRE-VALIDATE PDF CONTENT before uploading
            if file_name.lower().endswith('.pdf'):
                is_processable, pdf_error = self._validate_pdf_content(source_path)
                if not is_processable:
                    return False, pdf_error
            
            # Get user directory and target path
            user_path = self.get_user_documents_path(user_email)
            target_path = user_path / file_name
            
            print(f"Uploading {file_name} ({file_size / 1024:.1f} KB) to {target_path}")
            
            # Check if file already exists
            if target_path.exists():
                existing_size = target_path.stat().st_size
                if existing_size == file_size:
                    # Compare hashes for identical content
                    existing_hash = self.get_file_hash(target_path)
                    new_hash = self.get_file_hash(source_path)
                    
                    if existing_hash == new_hash:
                        return False, f"File '{file_name}' already exists with identical content."
                
                return False, f"File '{file_name}' already exists. Please rename or delete the existing file."
            
            # Copy file with error handling
            try:
                # Ensure target directory exists
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(source_path, target_path)
                
                # Verify copy was successful
                if not target_path.exists():
                    return False, f"File copy failed - target file not found after copy"
                
                copied_size = target_path.stat().st_size
                if copied_size != file_size:
                    target_path.unlink()  # Remove incomplete file
                    return False, f"File copy incomplete - size mismatch (expected {file_size}, got {copied_size})"
                
            except PermissionError:
                return False, f"Permission denied copying {file_name}"
            except OSError as e:
                return False, f"File system error copying {file_name}: {str(e)}"
            except Exception as e:
                return False, f"Error copying {file_name}: {str(e)}"
            
            # Calculate hash of copied file
            file_hash = self.get_file_hash(target_path)
            if not file_hash:
                print(f"Warning: Could not generate hash for {file_name}")
                file_hash = "unknown"
            
            # Store in database
            try:
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
                
                result = self.supabase.table("user_documents").insert(doc_data).execute()
                
                if not result.data:
                    # Remove file if database insert failed
                    if target_path.exists():
                        target_path.unlink()
                    return False, f"Database error storing {file_name} metadata"
                    
            except Exception as e:
                # Remove file if database insert failed
                if target_path.exists():
                    target_path.unlink()
                return False, f"Database error for {file_name}: {str(e)}"
            
            print(f"Successfully uploaded: {file_name} -> {target_path}")
            return True, f"File '{file_name}' uploaded successfully"
            
        except Exception as e:
            print(f"Unexpected error uploading file: {e}")
            return False, f"Upload error: {str(e)}"
    
    def _validate_pdf_content(self, file_path: Path) -> Tuple[bool, str]:
        """Pre-validate PDF to check if text can be extracted"""
        try:
            from langchain_community.document_loaders import PyPDFLoader, PyMuPDFLoader, PDFMinerLoader
            
            # Try PyPDFLoader first
            try:
                loader = PyPDFLoader(str(file_path))
                docs = loader.load()
                if docs and any(doc.page_content.strip() and len(doc.page_content.strip()) > 50 for doc in docs):
                    return True, ""
            except:
                pass
            
            # Try PyMuPDFLoader
            try:
                loader = PyMuPDFLoader(str(file_path))
                docs = loader.load()
                if docs and any(doc.page_content.strip() and len(doc.page_content.strip()) > 50 for doc in docs):
                    return True, ""
            except:
                pass
            
            # Try PDFMinerLoader
            try:
                loader = PDFMinerLoader(str(file_path))
                docs = loader.load()
                if docs and any(doc.page_content.strip() and len(doc.page_content.strip()) > 50 for doc in docs):
                    return True, ""
            except:
                pass
            
            # All loaders failed - this is likely an image-based PDF
            return False, f"PDF '{file_path.name}' is image-based and cannot be processed. Convert to text-searchable PDF or use .txt format."
            
        except Exception as e:
            print(f"Error validating PDF content: {e}")
            return True, ""  # Allow upload if validation fails
    
    def list_user_files(self, user_email: str) -> List[Dict]:
        """List all files for a user with error handling"""
        try:
            result = self.supabase.table("user_documents")\
                .select("*")\
                .eq("user_id", user_email)\
                .order("uploaded_at", desc=True)\
                .execute()
            
            files = result.data if result.data else []
            
            # Verify files still exist on filesystem
            verified_files = []
            user_path = self.get_user_documents_path(user_email)
            
            for file_info in files:
                file_path = user_path / file_info["file_name"]
                if file_path.exists():
                    verified_files.append(file_info)
                else:
                    print(f"Warning: Database record exists but file not found: {file_info['file_name']}")
                    # Optionally clean up orphaned database records
                    try:
                        self.supabase.table("user_documents")\
                            .delete()\
                            .eq("id", file_info["id"])\
                            .execute()
                        print(f"Cleaned up orphaned database record for {file_info['file_name']}")
                    except:
                        pass
            
            return verified_files
            
        except Exception as e:
            print(f"Error listing files: {e}")
            return []
    
    def delete_file(self, user_email: str, file_name: str) -> Tuple[bool, str]:
        """Delete a file for user with comprehensive cleanup"""
        try:
            # Get file info from database
            result = self.supabase.table("user_documents")\
                .select("*")\
                .eq("user_id", user_email)\
                .eq("file_name", file_name)\
                .execute()
            
            if not result.data:
                return False, f"File '{file_name}' not found in database"
            
            file_info = result.data[0]
            
            # Delete from filesystem
            user_path = self.get_user_documents_path(user_email)
            file_path = user_path / file_name
            
            filesystem_deleted = False
            if file_path.exists():
                try:
                    file_path.unlink()
                    filesystem_deleted = True
                    print(f"Deleted file from filesystem: {file_path}")
                except PermissionError:
                    return False, f"Permission denied deleting {file_name}"
                except Exception as e:
                    return False, f"Error deleting file {file_name}: {str(e)}"
            else:
                print(f"File not found on filesystem: {file_path}")
                filesystem_deleted = True  # Consider missing file as "deleted"
            
            # Delete from database
            try:
                self.supabase.table("user_documents")\
                    .delete()\
                    .eq("id", file_info["id"])\
                    .execute()
                print(f"Deleted database record for: {file_name}")
                
            except Exception as e:
                # If filesystem delete succeeded but database failed, 
                # we have an inconsistent state - warn user
                if filesystem_deleted:
                    return False, f"File deleted but database cleanup failed for {file_name}: {str(e)}"
                else:
                    return False, f"Database error deleting {file_name}: {str(e)}"
            
            return True, f"File '{file_name}' deleted successfully"
            
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False, f"Error deleting {file_name}: {str(e)}"
    
    def get_file_content(self, user_email: str, file_name: str) -> Optional[str]:
        """Get file content for processing with error handling"""
        try:
            user_path = self.get_user_documents_path(user_email)
            file_path = user_path / file_name
            
            if not file_path.exists():
                print(f"File not found: {file_path}")
                return None
            
            # Check file size before reading
            file_size = file_path.stat().st_size
            if file_size == 0:
                print(f"File is empty: {file_path}")
                return None
            
            # For text files, read content directly
            if file_path.suffix.lower() in ['.txt', '.md']:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    return content if content.strip() else None
                except UnicodeDecodeError:
                    # Try with different encodings
                    for encoding in ['latin-1', 'cp1252']:
                        try:
                            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                                content = f.read()
                            if content.strip():
                                return content
                        except:
                            continue
                    return None
            
            # For other files, return path for document loaders
            return str(file_path)
            
        except Exception as e:
            print(f"Error reading file content for {file_name}: {e}")
            return None
    
    def update_file_chunks_count(self, user_email: str, file_name: str, chunks_count: int):
        """Update chunks count after indexing with error handling"""
        try:
            result = self.supabase.table("user_documents")\
                .update({
                    "chunks_count": chunks_count,
                    "indexed_at": datetime.utcnow().isoformat()
                })\
                .eq("user_id", user_email)\
                .eq("file_name", file_name)\
                .execute()
            
            if result.data:
                print(f"Updated chunks count for {file_name}: {chunks_count}")
            else:
                print(f"Warning: No rows updated for {file_name} chunks count")
                
        except Exception as e:
            print(f"Error updating chunks count for {file_name}: {e}")
    
    def get_file_info(self, user_email: str, file_name: str) -> Optional[Dict]:
        """Get detailed file information"""
        try:
            result = self.supabase.table("user_documents")\
                .select("*")\
                .eq("user_id", user_email)\
                .eq("file_name", file_name)\
                .execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            print(f"Error getting file info for {file_name}: {e}")
            return None

# Global file service instance
file_service = FileService()