# rag_service.py - Clean RAG service with enhanced indexing
import os
import warnings
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="langchain")

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, Docx2txtLoader, UnstructuredMarkdownLoader
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
    """RAG service using ChromaDB and LangChain"""
    
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
        """Load document using appropriate loader"""
        try:
            file_path_obj = Path(file_path)
            
            if file_path_obj.suffix.lower() == '.txt':
                loader = TextLoader(str(file_path_obj), encoding='utf-8')
            elif file_path_obj.suffix.lower() == '.md':
                loader = UnstructuredMarkdownLoader(str(file_path_obj))
            elif file_path_obj.suffix.lower() == '.pdf':
                loader = PyPDFLoader(str(file_path_obj))
            elif file_path_obj.suffix.lower() == '.docx':
                loader = Docx2txtLoader(str(file_path_obj))
            else:
                print(f"Unsupported file type: {file_path_obj}")
                return []
            
            docs = loader.load()
            
            # Add metadata with proper file name for citation
            for doc in docs:
                doc.metadata.update({
                    'source': file_path_obj.name,
                    'file_path': str(file_path_obj),
                    'indexed_at': datetime.utcnow().isoformat()
                })
            
            return docs
            
        except Exception as e:
            print(f"Error loading document {file_path}: {e}")
            return []
    
    def index_user_document(self, user_email: str, file_name: str) -> Tuple[bool, str, int]:
        """Index a document for a specific user with enhanced error handling"""
        try:
            user_path = file_service.get_user_documents_path(user_email)
            file_path = user_path / file_name
            
            if not file_path.exists():
                return False, f"File {file_name} not found", 0
            
            try:
                docs = self.load_document(str(file_path))
                if not docs:
                    return False, f"Could not load document {file_name}", 0
            except Exception as e:
                return False, f"Error loading {file_name}: {str(e)}", 0
            
            try:
                chunks = self.text_splitter.split_documents(docs)
                if not chunks:
                    return False, f"No chunks created from {file_name}", 0
            except Exception as e:
                return False, f"Error processing {file_name}: {str(e)}", 0
            
            # Add chunk metadata with proper source citation
            for i, chunk in enumerate(chunks):
                chunk.metadata.update({
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'user_id': user_email,
                    'file_name': file_name,
                    'source': file_name
                })
            
            try:
                vectorstore = self.get_user_vectorstore(user_email)
                
                # Process in batches for large files
                batch_size = 50
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i:i+batch_size]
                    vectorstore.add_documents(batch)
                
            except Exception as e:
                return False, f"Error indexing {file_name}: {str(e)}", 0
            
            try:
                file_service.update_file_chunks_count(user_email, file_name, len(chunks))
            except Exception as e:
                print(f"Warning: Could not update database: {e}")
            
            print(f"✅ Indexed {file_name}: {len(chunks)} chunks")
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
                    'similarity_score': float(similarity)
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
                print(f"✅ Removed {len(results['ids'])} chunks for {file_name}")
            
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