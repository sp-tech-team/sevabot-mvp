# rag_service.py - Enhanced RAG service for common knowledge repository
import os
import warnings
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import time

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="langchain")

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, Docx2txtLoader, PyMuPDFLoader
)
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
from fastapi import APIRouter

from config import (
    RAG_INDEX_PATH, OPENAI_API_KEY, EMBEDDING_MODEL,
    CHUNK_SIZE, CHUNK_OVERLAP, TOP_K, COMMON_KNOWLEDGE_PATH,
    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, IS_PRODUCTION
)
from file_service import file_service

class RAGService:
    """Enhanced RAG service for common knowledge repository"""
    
    def __init__(self):
        self.index_path = Path(RAG_INDEX_PATH)
        self.index_path.mkdir(exist_ok=True)
        
        self.embeddings = OpenAIEmbeddings(
            api_key=OPENAI_API_KEY,
            model=EMBEDDING_MODEL
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        self._common_vectorstore = None
        # FIXED: Store chunks count locally for development mode
        self._dev_chunks_count = {}
    
    def get_common_knowledge_vectorstore(self) -> Chroma:
        """Get or create common knowledge vector store"""
        if self._common_vectorstore is None:
            chroma_path = self.index_path / "common_knowledge"
            chroma_path.mkdir(exist_ok=True)
            
            self._common_vectorstore = Chroma(
                persist_directory=str(chroma_path),
                embedding_function=self.embeddings,
                collection_name="common_knowledge"
            )
        
        return self._common_vectorstore
    
    def load_document(self, file_path: str) -> Tuple[List[Document], bool]:
        """Load document with OCR rejection - returns (docs, used_ocr)"""
        try:
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                print(f"File not found: {file_path_obj}")
                return [], False
            
            file_size = file_path_obj.stat().st_size
            if file_size == 0:
                print(f"File is empty: {file_path_obj}")
                return [], False
            
            print(f"Loading document: {file_path_obj.name} ({file_size / (1024*1024):.2f} MB)")
            
            docs = []
            used_ocr = False
            
            if file_path_obj.suffix.lower() in ['.txt', '.md']:
                loader = TextLoader(str(file_path_obj), encoding='utf-8', autodetect_encoding=True)
                docs = loader.load()
                
            elif file_path_obj.suffix.lower() == '.pdf':
                # Try multiple PDF loaders
                content_found = False
                
                # PyPDFLoader first
                try:
                    loader = PyPDFLoader(str(file_path_obj))
                    docs = loader.load()
                    if docs and any(doc.page_content.strip() and len(doc.page_content.strip()) > 50 for doc in docs):
                        content_found = True
                        print(f"Extracted with PyPDFLoader")
                except Exception as e:
                    print(f"PyPDFLoader failed: {e}")
                
                # PyMuPDFLoader as fallback
                if not content_found:
                    try:
                        loader = PyMuPDFLoader(str(file_path_obj))
                        docs = loader.load()
                        if docs and any(doc.page_content.strip() and len(doc.page_content.strip()) > 50 for doc in docs):
                            content_found = True
                            print(f"Extracted with PyMuPDFLoader")
                    except Exception as e:
                        print(f"PyMuPDFLoader failed: {e}")
                
                # If normal PDF extraction fails, reject the file instead of using OCR
                if not content_found:
                    print(f"All standard PDF extraction methods failed for: {file_path_obj}")
                    print(f"OCR would be required - rejecting file as per policy")
                    return [], True  # Return True to indicate OCR would be needed
                
            elif file_path_obj.suffix.lower() == '.docx':
                loader = Docx2txtLoader(str(file_path_obj))
                docs = loader.load()
            else:
                print(f"Unsupported file type: {file_path_obj.suffix}")
                return [], False
            
            if not docs:
                return [], used_ocr
            
            # Add metadata
            valid_docs = []
            for doc in docs:
                if doc.page_content and len(doc.page_content.strip()) > 0:
                    doc.metadata.update({
                        'source': file_path_obj.name,
                        'file_name': file_path_obj.name,
                        'file_path': str(file_path_obj),
                        'file_size': file_size,
                        'indexed_at': datetime.utcnow().isoformat(),
                        'content_length': len(doc.page_content),
                        'is_common_knowledge': True
                    })
                    valid_docs.append(doc)
            
            print(f"Loaded {len(valid_docs)} valid documents from {file_path_obj.name}")
            return valid_docs, used_ocr
            
        except Exception as e:
            print(f"Error loading document {file_path}: {e}")
            return [], False
    
    def index_common_knowledge_document(self, file_name: str) -> Tuple[bool, str, int]:
        """Index document in common knowledge repository"""
        try:
            file_path = file_service.get_common_knowledge_path() / file_name
            
            if not file_path.exists():
                return False, f"File {file_name} not found in common knowledge repository", 0
            
            print(f"Indexing: {file_name}")
            
            # Load document with OCR check
            docs, used_ocr = self.load_document(str(file_path))
            
            # Reject if OCR would be needed
            if used_ocr:
                return False, f"{file_name} requires OCR processing which is not supported. Please upload text-extractable PDFs only (max 10MB, .txt/.md/.pdf/.docx allowed).", 0
            
            if not docs:
                return False, f"Could not extract content from {file_name}", 0
            
            # Check if already indexed
            vectorstore = self.get_common_knowledge_vectorstore()
            collection = vectorstore._collection
            
            # Check for existing chunks
            existing_results = collection.get(where={"file_name": file_name})
            if existing_results and existing_results['ids']:
                existing_chunks = len(existing_results['ids'])
                print(f"File {file_name} already indexed with {existing_chunks} chunks - skipping")
                
                # FIXED: Update chunks count for both dev and production
                if IS_PRODUCTION:
                    try:
                        file_service.update_common_knowledge_file_chunks_count(file_name, existing_chunks)
                    except Exception as e:
                        print(f"Warning: Could not update database chunks count: {e}")
                else:
                    # Store in memory for development
                    self._dev_chunks_count[file_name] = existing_chunks
                
                return True, f"{file_name} already indexed ({existing_chunks} chunks)", existing_chunks
            
            # Split into chunks
            chunks = []
            for doc in docs:
                doc_chunks = self.text_splitter.split_documents([doc])
                chunks.extend(doc_chunks)
            
            if not chunks:
                return False, f"No chunks created from {file_name}", 0
            
            # Add metadata to chunks
            for i, chunk in enumerate(chunks):
                chunk.metadata.update({
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'file_name': file_name,
                    'source': file_name,
                    'chunk_size': len(chunk.page_content),
                    'is_common_knowledge': True
                })
            
            # Index chunks in batches
            batch_size = 20
            successful_batches = 0
            total_batches = (len(chunks) + batch_size - 1) // batch_size
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i+batch_size]
                batch_num = (i // batch_size) + 1
                
                for attempt in range(3):
                    try:
                        vectorstore.add_documents(batch)
                        successful_batches += 1
                        print(f"Processed batch {batch_num}/{total_batches}")
                        break
                    except Exception as e:
                        if attempt == 2:
                            return False, f"Failed to index batch {batch_num}: {e}", 0
                        time.sleep(1)
            
            # FIXED: Update chunks count for both dev and production
            if IS_PRODUCTION:
                try:
                    file_service.update_common_knowledge_file_chunks_count(file_name, len(chunks))
                except Exception as e:
                    print(f"Warning: Could not update database chunks count: {e}")
            else:
                # Store in memory for development
                self._dev_chunks_count[file_name] = len(chunks)
            
            print(f"Successfully indexed {file_name}: {len(chunks)} chunks")
            return True, f"Successfully indexed {file_name}", len(chunks)
            
        except Exception as e:
            print(f"Error indexing {file_name}: {e}")
            return False, f"Error indexing {file_name}: {str(e)}", 0
    
    def get_file_chunks_count(self, file_name: str) -> int:
        """Get chunks count for a file (dev-aware)"""
        if IS_PRODUCTION:
            # Production: Get from database
            try:
                file_info = file_service.get_common_knowledge_file_info(file_name)
                return file_info.get("chunks_count", 0) if file_info else 0
            except Exception:
                return 0
        else:
            # Development: Get from memory or vector store
            if file_name in self._dev_chunks_count:
                return self._dev_chunks_count[file_name]
            
            # Check vector store directly
            try:
                vectorstore = self.get_common_knowledge_vectorstore()
                collection = vectorstore._collection
                existing_results = collection.get(where={"file_name": file_name})
                chunks_count = len(existing_results['ids']) if existing_results and existing_results['ids'] else 0
                self._dev_chunks_count[file_name] = chunks_count
                return chunks_count
            except Exception:
                return 0
    
    def reindex_common_knowledge_pending_files(self) -> Tuple[int, int, List[str]]:
        """Re-index only files that are not yet indexed in common knowledge repository"""
        try:
            files = file_service.list_common_knowledge_files()
            
            # Get currently indexed files from vector store
            vectorstore = self.get_common_knowledge_vectorstore()
            collection = vectorstore._collection
            
            indexed_files = set()
            try:
                all_docs = collection.get()
                if all_docs and all_docs.get('metadatas'):
                    for metadata in all_docs['metadatas']:
                        file_name = metadata.get('file_name') or metadata.get('source', '')
                        if file_name:
                            indexed_files.add(file_name)
            except Exception as e:
                print(f"Error getting indexed files: {e}")
            
            # Filter to only pending files (not in vector store)
            pending_files = [f for f in files if f["file_name"] not in indexed_files]
            
            if not pending_files:
                return 0, len(files), []
            
            reindexed = 0
            errors = []
            
            for file_info in pending_files:
                file_name = file_info["file_name"]
                try:
                    success, msg, chunks = self.index_common_knowledge_document(file_name)
                    if success and not msg.startswith("✅"):  # Don't count "already indexed" as reindexed
                        reindexed += 1
                    elif not success:
                        errors.append(f"{file_name}: {msg}")
                        
                except Exception as e:
                    errors.append(f"{file_name}: {str(e)}")
            
            return reindexed, len(pending_files), errors
            
        except Exception as e:
            print(f"Error in reindex: {e}")
            return 0, 0, [str(e)]
    
    def search_common_knowledge(self, query: str, top_k: int = None) -> List[Tuple[str, str, float, Dict]]:
        """Search common knowledge repository"""
        if top_k is None:
            top_k = TOP_K
        
        try:
            vectorstore = self.get_common_knowledge_vectorstore()
            collection = vectorstore._collection
            
            if collection.count() == 0:
                return []
            
            results = vectorstore.similarity_search_with_score(query, k=top_k)
            
            formatted_results = []
            for doc, score in results:
                chunk = doc.page_content
                source = doc.metadata.get('source', 'Unknown')
                file_name = doc.metadata.get('file_name', source)
                
                similarity = max(0, 1 - score) if score <= 1 else 1 / (1 + score)
                
                metadata = {
                    'source': source,
                    'file_name': file_name,
                    'chunk_index': doc.metadata.get('chunk_index', 0),
                    'similarity_score': float(similarity),
                    'chunk_size': doc.metadata.get('chunk_size', len(chunk)),
                    'is_common_knowledge': True
                }
                
                formatted_results.append((chunk, file_name, float(similarity), metadata))
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching common knowledge: {e}")
            return []
    
    def remove_common_knowledge_document(self, file_name: str) -> bool:
        """Remove document from common knowledge vector store"""
        try:
            vectorstore = self.get_common_knowledge_vectorstore()
            collection = vectorstore._collection
            results = collection.get(where={"file_name": file_name})
            
            if results['ids']:
                collection.delete(ids=results['ids'])
                print(f"Removed {len(results['ids'])} chunks for {file_name}")
                
                # FIXED: Update chunks count for both dev and production
                if IS_PRODUCTION:
                    try:
                        file_service.update_common_knowledge_file_chunks_count(file_name, 0)
                    except Exception as e:
                        print(f"Warning: Could not update database chunks count: {e}")
                else:
                    # Remove from memory for development
                    self._dev_chunks_count.pop(file_name, None)
            
            return True
            
        except Exception as e:
            print(f"Error removing document: {e}")
            return False
    
    def get_common_knowledge_document_count(self) -> int:
        """Get document count in common knowledge vector store"""
        try:
            vectorstore = self.get_common_knowledge_vectorstore()
            return vectorstore._collection.count()
        except Exception:
            return 0

    def cleanup_common_knowledge_orphaned_vectors(self) -> Tuple[int, int, List[str]]:
        """Clean up vector entries for files that don't exist on disk in common knowledge repository"""
        try:
            # Get actual files on disk
            actual_files = set()
            common_knowledge_path = file_service.get_common_knowledge_path()
            
            if common_knowledge_path.exists():
                for file_path in common_knowledge_path.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.pdf', '.docx']:
                        actual_files.add(file_path.name)
            
            # Get vector store
            vectorstore = self.get_common_knowledge_vectorstore()
            collection = vectorstore._collection
            
            try:
                all_docs = collection.get()
                if not all_docs or not all_docs.get('metadatas'):
                    return 0, 0, []
                
                # Find orphaned entries
                orphaned_ids = []
                orphaned_files = set()
                
                for doc_id, metadata in zip(all_docs['ids'], all_docs['metadatas']):
                    file_name = metadata.get('file_name') or metadata.get('source', '')
                    if file_name and file_name not in actual_files:
                        orphaned_ids.append(doc_id)
                        orphaned_files.add(file_name)
                
                # Remove orphaned entries in batches
                cleanup_count = 0
                if orphaned_ids:
                    batch_size = 100
                    for i in range(0, len(orphaned_ids), batch_size):
                        batch_ids = orphaned_ids[i:i+batch_size]
                        try:
                            collection.delete(ids=batch_ids)
                            cleanup_count += len(batch_ids)
                        except Exception as e:
                            print(f"Error deleting batch: {e}")
                
                # FIXED: Clean up dev chunks count for orphaned files
                if not IS_PRODUCTION:
                    for orphaned_file in orphaned_files:
                        self._dev_chunks_count.pop(orphaned_file, None)
                
                return cleanup_count, len(actual_files), list(orphaned_files)
                
            except Exception as e:
                print(f"Error accessing vector store: {e}")
                return 0, 0, []
            
        except Exception as e:
            print(f"Error in cleanup: {e}")
            return 0, 0, []

# Global RAG service instance
rag_service = RAGService()

# API Router for RAG endpoints
router = APIRouter(tags=["RAG"])

@router.post("/api/cleanup-common-knowledge-vector-db")
async def cleanup_common_knowledge_vector_database():
    """Clean up common knowledge vector database - remove entries for non-existent files"""
    try:
        cleanup_count, remaining_files, orphaned_files = rag_service.cleanup_common_knowledge_orphaned_vectors()
        
        # Also clean up database records
        db_cleanup_count = 0
        try:
            from supabase import create_client
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            
            common_knowledge_path = file_service.get_common_knowledge_path()
            actual_files = set()
            
            if common_knowledge_path.exists():
                for file_path in common_knowledge_path.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.pdf', '.docx']:
                        actual_files.add(file_path.name)
            
            # Get database records
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
                            print(f"Error deleting DB record: {e}")
        
        except Exception as e:
            print(f"Database cleanup error: {e}")
        
        return {
            "status": "success",
            "vector_entries_cleaned": cleanup_count,
            "db_records_cleaned": db_cleanup_count,
            "remaining_files": remaining_files,
            "orphaned_files": orphaned_files,
            "message": f"Cleaned {cleanup_count} vector entries and {db_cleanup_count} DB records. {remaining_files} files remain."
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "vector_entries_cleaned": 0,
            "db_records_cleaned": 0,
            "remaining_files": 0,
            "orphaned_files": []
        }

@router.get("/api/common-knowledge-vector-stats")
async def get_common_knowledge_vector_stats():
    """Get vector database statistics for common knowledge repository"""
    try:
        doc_count = rag_service.get_common_knowledge_document_count()
        
        # Get file system stats
        common_knowledge_path = file_service.get_common_knowledge_path()
        fs_files = 0
        
        if common_knowledge_path.exists():
            for file_path in common_knowledge_path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.pdf', '.docx']:
                    fs_files += 1
        
        return {
            "vector_entries": doc_count,
            "filesystem_files": fs_files,
            "sync_status": "synced" if doc_count > 0 and fs_files > 0 else "needs_cleanup"
        }
        
    except Exception as e:
        return {
            "vector_entries": 0,
            "filesystem_files": 0,
            "sync_status": "error",
            "error": str(e)
        }