# rag_service.py - Enhanced RAG service with better file processing
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

from config import (
    RAG_INDEX_PATH, OPENAI_API_KEY, EMBEDDING_MODEL,
    CHUNK_SIZE, CHUNK_OVERLAP, TOP_K
)
from file_service import file_service

class RAGService:
    """Enhanced RAG service with better error handling and file processing"""
    
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
        
        self._user_vectorstores = {}
    
    def get_user_vectorstore(self, user_email: str) -> Chroma:
        """Get or create user-specific vector store"""
        if user_email not in self._user_vectorstores:
            user_folder = user_email.replace("@", "_").replace(".", "_")
            chroma_path = self.index_path / user_folder
            chroma_path.mkdir(exist_ok=True)
            
            self._user_vectorstores[user_email] = Chroma(
                persist_directory=str(chroma_path),
                embedding_function=self.embeddings,
                collection_name="user_documents"
            )
        
        return self._user_vectorstores[user_email]
    
    def load_document(self, file_path: str) -> List[Document]:
        """Load document using appropriate loader with enhanced error handling"""
        try:
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                print(f"File not found: {file_path_obj}")
                return []
            
            # Check file size
            file_size = file_path_obj.stat().st_size
            if file_size == 0:
                print(f"File is empty: {file_path_obj}")
                return []
            
            print(f"Loading document: {file_path_obj.name} ({file_size / (1024*1024):.2f} MB)")
            
            docs = []
            
            if file_path_obj.suffix.lower() == '.txt':
                loader = TextLoader(str(file_path_obj), encoding='utf-8', autodetect_encoding=True)
                docs = loader.load()
                
            elif file_path_obj.suffix.lower() == '.md':
                # Use TextLoader for markdown files instead of UnstructuredMarkdownLoader
                loader = TextLoader(str(file_path_obj), encoding='utf-8', autodetect_encoding=True)
                docs = loader.load()
                
            elif file_path_obj.suffix.lower() == '.pdf':
                # Try multiple LangChain PDF loaders in order
                content_found = False
                docs = []
                
                # 1. First try PyPDFLoader (fastest for text-based PDFs)
                try:
                    loader = PyPDFLoader(str(file_path_obj))
                    docs = loader.load()
                    
                    if docs and any(doc.page_content.strip() and len(doc.page_content.strip()) > 50 for doc in docs):
                        content_found = True
                        print(f"Successfully extracted with PyPDFLoader")
                except Exception as e:
                    print(f"PyPDFLoader failed: {e}")
                
                # 2. If PyPDFLoader failed, try PyMuPDFLoader (better for complex/image PDFs)
                if not content_found:
                    print(f"Trying PyMuPDFLoader for: {file_path_obj}")
                    try:
                        loader = PyMuPDFLoader(str(file_path_obj))
                        docs = loader.load()
                        
                        if docs and any(doc.page_content.strip() and len(doc.page_content.strip()) > 50 for doc in docs):
                            content_found = True
                            print(f"Successfully extracted with PyMuPDFLoader")
                    except Exception as e:
                        print(f"PyMuPDFLoader failed: {e}")
                
                # 3. If still no content, try OCR as final fallback
                if not content_found:
                    print(f"Trying OCR extraction for: {file_path_obj}")
                    try:
                        import easyocr
                        import fitz  # pymupdf for image extraction
                        
                        reader = easyocr.Reader(['en'], verbose=False)
                        doc = fitz.open(str(file_path_obj))
                        
                        extracted_text = ""
                        for page_num, page in enumerate(doc):
                            try:
                                # Convert page to image
                                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scaling for better OCR
                                img_data = pix.tobytes("png")
                                
                                # Extract text using OCR
                                results = reader.readtext(img_data, paragraph=True)
                                page_text = "\n".join([item[1] for item in results if item[1].strip()])
                                
                                if page_text.strip():
                                    extracted_text += f"\n\nPage {page_num + 1}:\n{page_text}"
                                    print(f"OCR Page {page_num + 1}: extracted {len(page_text)} characters")
                                    
                            except Exception as page_error:
                                print(f"OCR failed for page {page_num + 1}: {page_error}")
                        
                        doc.close()
                        
                        if extracted_text.strip():
                            from langchain.schema import Document
                            docs = [Document(page_content=extracted_text.strip())]
                            content_found = True
                            print(f"Successfully extracted text using OCR: {len(extracted_text)} characters")
                        
                    except ImportError:
                        print("easyocr not installed. Install with: pip install easyocr")
                    except Exception as e:
                        print(f"OCR processing failed: {e}")
                
                if not content_found:
                    print(f"All extraction methods failed for: {file_path_obj}")
                    return []
                
            elif file_path_obj.suffix.lower() == '.docx':
                loader = Docx2txtLoader(str(file_path_obj))
                docs = loader.load()
                
            else:
                print(f"Unsupported file type: {file_path_obj.suffix}")
                return []
            
            if not docs:
                print(f"No content extracted from: {file_path_obj}")
                return []
            
            # Validate document content
            valid_docs = []
            for doc in docs:
                if doc.page_content and len(doc.page_content.strip()) > 0:
                    # Add comprehensive metadata
                    doc.metadata.update({
                        'source': file_path_obj.name,
                        'file_name': file_path_obj.name,
                        'file_path': str(file_path_obj),
                        'file_size': file_size,
                        'indexed_at': datetime.utcnow().isoformat(),
                        'content_length': len(doc.page_content)
                    })
                    valid_docs.append(doc)
            
            print(f"Successfully loaded {len(valid_docs)} valid documents from {file_path_obj.name}")
            return valid_docs
            
        except UnicodeDecodeError as e:
            print(f"Encoding error loading {file_path}: {e}")
            # Try with different encodings
            try:
                if file_path_obj.suffix.lower() == '.txt':
                    for encoding in ['utf-8', 'latin-1', 'cp1252']:
                        try:
                            loader = TextLoader(str(file_path_obj), encoding=encoding)
                            docs = loader.load()
                            if docs:
                                print(f"Successfully loaded with {encoding} encoding")
                                return docs
                        except:
                            continue
            except:
                pass
            return []
            
        except Exception as e:
            print(f"Error loading document {file_path}: {e}")
            return []
    
    def index_user_document(self, user_email: str, file_name: str) -> Tuple[bool, str, int]:
        """Index a document with comprehensive error handling and retry logic"""
        try:
            user_path = file_service.get_user_documents_path(user_email)
            file_path = user_path / file_name
            
            if not file_path.exists():
                return False, f"File {file_name} not found", 0
            
            print(f"Starting indexing process for: {file_name}")
            
            # Step 1: Load document
            try:
                docs = self.load_document(str(file_path))
                if not docs:
                    return False, f"Could not load or extract content from {file_name}", 0
                    
                print(f"Loaded {len(docs)} documents from {file_name}")
                
            except Exception as e:
                return False, f"Error loading {file_name}: {str(e)}", 0
            
            # Step 2: Split into chunks
            try:
                chunks = []
                for doc in docs:
                    doc_chunks = self.text_splitter.split_documents([doc])
                    chunks.extend(doc_chunks)
                
                if not chunks:
                    return False, f"No chunks created from {file_name} - content may be too short", 0
                    
                print(f"Created {len(chunks)} chunks from {file_name}")
                
            except Exception as e:
                return False, f"Error processing {file_name}: {str(e)}", 0
            
            # Step 3: Add metadata to chunks
            for i, chunk in enumerate(chunks):
                chunk.metadata.update({
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'user_id': user_email,
                    'file_name': file_name,
                    'source': file_name,
                    'chunk_size': len(chunk.page_content)
                })
            
            # Step 4: Index chunks in batches
            try:
                vectorstore = self.get_user_vectorstore(user_email)
                
                # Process in smaller batches for large files
                batch_size = 20 if len(chunks) > 100 else 50
                successful_batches = 0
                total_batches = (len(chunks) + batch_size - 1) // batch_size
                
                print(f"Processing {len(chunks)} chunks in {total_batches} batches of {batch_size}")
                
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i:i+batch_size]
                    batch_num = (i // batch_size) + 1
                    
                    try:
                        # Add batch with retry logic
                        retry_count = 0
                        max_retries = 3
                        batch_success = False
                        
                        while retry_count < max_retries and not batch_success:
                            try:
                                vectorstore.add_documents(batch)
                                batch_success = True
                                successful_batches += 1
                                print(f"Successfully processed batch {batch_num}/{total_batches}")
                                
                            except Exception as batch_error:
                                retry_count += 1
                                if retry_count < max_retries:
                                    print(f"Batch {batch_num} failed, retrying ({retry_count}/{max_retries}): {batch_error}")
                                    time.sleep(1)  # Brief delay before retry
                                else:
                                    print(f"Batch {batch_num} failed after {max_retries} attempts: {batch_error}")
                        
                        if not batch_success:
                            return False, f"Failed to index batch {batch_num} of {file_name} after {max_retries} attempts", 0
                            
                    except Exception as e:
                        return False, f"Error indexing batch {batch_num} of {file_name}: {str(e)}", 0
                
                if successful_batches != total_batches:
                    return False, f"Only {successful_batches}/{total_batches} batches indexed successfully", 0
                
            except Exception as e:
                return False, f"Error indexing {file_name}: {str(e)}", 0
            
            # Step 5: Update database
            try:
                file_service.update_file_chunks_count(user_email, file_name, len(chunks))
            except Exception as e:
                print(f"Warning: Could not update database: {e}")
            
            print(f"Successfully indexed {file_name}: {len(chunks)} chunks in {successful_batches} batches")
            return True, f"Successfully indexed {file_name}", len(chunks)
            
        except Exception as e:
            print(f"Error indexing {file_name}: {e}")
            return False, f"Error indexing {file_name}: {str(e)}", 0
    
    def search_user_documents(self, user_email: str, query: str, top_k: int = None) -> List[Tuple[str, str, float, Dict]]:
        """Search user's documents and return with proper source citation"""
        if top_k is None:
            top_k = TOP_K
        
        try:
            vectorstore = self.get_user_vectorstore(user_email)
            
            collection = vectorstore._collection
            count = collection.count()
            
            if count == 0:
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
                    'chunk_size': doc.metadata.get('chunk_size', len(chunk))
                }
                
                formatted_results.append((chunk, file_name, float(similarity), metadata))
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching documents: {e}")
            return []
    
    def remove_user_document(self, user_email: str, file_name: str) -> bool:
        """Remove document from user's vector store"""
        try:
            vectorstore = self.get_user_vectorstore(user_email)
            
            collection = vectorstore._collection
            results = collection.get(where={"file_name": file_name})
            
            if results['ids']:
                collection.delete(ids=results['ids'])
                print(f"Removed {len(results['ids'])} chunks for {file_name}")
            
            return True
            
        except Exception as e:
            print(f"Error removing document from vector store: {e}")
            return False
    
    def get_user_document_count(self, user_email: str) -> int:
        """Get number of documents in user's vector store"""
        try:
            vectorstore = self.get_user_vectorstore(user_email)
            collection = vectorstore._collection
            return collection.count()
        except Exception:
            return 0

# Global RAG service instance
rag_service = RAGService()