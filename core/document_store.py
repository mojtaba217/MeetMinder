"""
Document Store for MeetMinder - Multi-file knowledge base with RAG support
Supports both offline (local embeddings + FAISS) and online (cloud embeddings + vector DB) modes
"""

import asyncio
import hashlib
import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import numpy as np

@dataclass
class DocumentChunk:
    """Represents a chunk of document content with metadata"""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None
    file_path: str = ""
    chunk_index: int = 0
    total_chunks: int = 1

@dataclass
class DocumentInfo:
    """Metadata about a document"""
    id: str
    file_path: str
    file_name: str
    file_size: int
    mime_type: str
    last_modified: float
    status: str = "pending"  # pending, processing, completed, failed
    chunks_count: int = 0
    error_message: str = ""

class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers"""

    @abstractmethod
    async def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text"""
        pass

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """Embed multiple texts"""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return embedding dimension"""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider is available"""
        pass

class VectorBackend(ABC):
    """Abstract base class for vector storage backends"""

    @abstractmethod
    async def upsert(self, chunk: DocumentChunk) -> bool:
        """Store a document chunk"""
        pass

    @abstractmethod
    async def search(self, query_embedding: np.ndarray, top_k: int = 5,
                    filter_dict: Optional[Dict[str, Any]] = None) -> List[Tuple[DocumentChunk, float]]:
        """Search for similar chunks"""
        pass

    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a document"""
        pass

    @abstractmethod
    async def get_document_chunks(self, document_id: str) -> List[DocumentChunk]:
        """Get all chunks for a document"""
        pass

    @abstractmethod
    async def save(self) -> bool:
        """Persist data to disk"""
        pass

    @abstractmethod
    async def load(self) -> bool:
        """Load data from disk"""
        pass

class DocumentStore:
    """Main document store with pluggable embeddings and vector backends"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.data_dir = Path(config.get('data_dir', 'data/user_documents'))
        self.data_dir.mkdir(exist_ok=True)

        self.metadata_file = self.data_dir / 'documents_metadata.json'
        self.documents: Dict[str, DocumentInfo] = {}

        # Initialize components
        self.embedding_provider: Optional[EmbeddingProvider] = None
        self.vector_backend: Optional[VectorBackend] = None

        # Chunking settings
        self.chunk_size = config.get('chunk_size', 1000)
        self.chunk_overlap = config.get('chunk_overlap', 200)

        # Load existing metadata
        self._load_metadata()

    async def initialize(self) -> bool:
        """Initialize embedding provider and vector backend"""
        try:
            # Initialize embedding provider
            embedding_config = self.config.get('embedding', {})
            provider_type = embedding_config.get('provider', 'local')

            if provider_type == 'local':
                from .embeddings.local_embeddings import LocalEmbeddingProvider
                self.embedding_provider = LocalEmbeddingProvider(embedding_config)
            elif provider_type == 'openai':
                from .embeddings.openai_embeddings import OpenAIEmbeddingProvider
                self.embedding_provider = OpenAIEmbeddingProvider(embedding_config)
            else:
                raise ValueError(f"Unsupported embedding provider: {provider_type}")

            # Initialize vector backend
            vector_config = self.config.get('vector', {})
            backend_type = vector_config.get('backend', 'faiss')

            if backend_type == 'faiss':
                from .vector.faiss_backend import FAISSBackend
                self.vector_backend = FAISSBackend(vector_config, self.data_dir)
            elif backend_type == 'pinecone':
                from .vector.pinecone_backend import PineconeBackend
                self.vector_backend = PineconeBackend(vector_config)
            else:
                raise ValueError(f"Unsupported vector backend: {backend_type}")

            # Load existing vector data
            await self.vector_backend.load()

            return True
        except Exception as e:
            print(f"Failed to initialize DocumentStore: {e}")
            return False

    async def add_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a file to the document store"""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Generate document ID
        doc_id = self._generate_document_id(file_path)

        # Create document info
        doc_info = DocumentInfo(
            id=doc_id,
            file_path=str(file_path),
            file_name=file_path.name,
            file_size=file_path.stat().st_size,
            mime_type=self._get_mime_type(file_path),
            last_modified=file_path.stat().st_mtime,
            status="processing"
        )

        if metadata:
            doc_info.metadata.update(metadata)

        self.documents[doc_id] = doc_info
        self._save_metadata()

        return doc_id

    async def process_document(self, doc_id: str) -> bool:
        """Process a document: extract text, chunk, embed, and store"""
        if doc_id not in self.documents:
            return False

        doc_info = self.documents[doc_id]
        doc_info.status = "processing"
        self._save_metadata()

        try:
            # Extract text from file
            text = await self._extract_text(doc_info.file_path)
            if not text:
                raise ValueError("No text could be extracted from file")

            # Chunk the text
            chunks = self._chunk_text(text, doc_info)

            # Generate embeddings
            if not self.embedding_provider:
                raise ValueError("Embedding provider not initialized")

            texts_to_embed = [chunk.content for chunk in chunks]
            embeddings = await self.embedding_provider.embed_texts(texts_to_embed)

            # Add embeddings to chunks
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding

            # Store chunks in vector backend
            if not self.vector_backend:
                raise ValueError("Vector backend not initialized")

            for chunk in chunks:
                await self.vector_backend.upsert(chunk)

            # Update document status
            doc_info.status = "completed"
            doc_info.chunks_count = len(chunks)

        except Exception as e:
            doc_info.status = "failed"
            doc_info.error_message = str(e)
            print(f"Failed to process document {doc_id}: {e}")

        self._save_metadata()
        await self.vector_backend.save()
        return doc_info.status == "completed"

    async def query(self, query: str, top_k: int = 5,
                   filter_dict: Optional[Dict[str, Any]] = None) -> List[Tuple[DocumentChunk, float]]:
        """Query the document store for relevant chunks"""
        if not self.embedding_provider or not self.vector_backend:
            return []

        # Generate query embedding
        query_embedding = await self.embedding_provider.embed_text(query)

        # Search vector backend
        return await self.vector_backend.search(query_embedding, top_k, filter_dict)

    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document and all its chunks"""
        if doc_id not in self.documents:
            return False

        # Delete from vector backend
        if self.vector_backend:
            await self.vector_backend.delete_document(doc_id)

        # Remove from documents
        del self.documents[doc_id]
        self._save_metadata()

        # Remove file if it exists in our data directory
        doc_info = self.documents.get(doc_id)
        if doc_info and doc_info.file_path.startswith(str(self.data_dir)):
            try:
                Path(doc_info.file_path).unlink(missing_ok=True)
            except Exception as e:
                print(f"Failed to delete file {doc_info.file_path}: {e}")

        return True

    def list_documents(self) -> List[DocumentInfo]:
        """List all documents"""
        return list(self.documents.values())

    def get_document_info(self, doc_id: str) -> Optional[DocumentInfo]:
        """Get information about a specific document"""
        return self.documents.get(doc_id)

    async def _extract_text(self, file_path: str) -> str:
        """Extract text from various file formats"""
        from .extractors.file_extractor import FileExtractor
        extractor = FileExtractor()
        return await extractor.extract_text(file_path)

    def _chunk_text(self, text: str, doc_info: DocumentInfo) -> List[DocumentChunk]:
        """Split text into chunks"""
        chunks = []
        words = text.split()
        chunk_index = 0

        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = ' '.join(chunk_words)

            if len(chunk_text.strip()) < 50:  # Skip very small chunks
                continue

            chunk = DocumentChunk(
                id=f"{doc_info.id}_chunk_{chunk_index}",
                content=chunk_text,
                metadata={
                    'document_id': doc_info.id,
                    'file_name': doc_info.file_name,
                    'mime_type': doc_info.mime_type
                },
                file_path=doc_info.file_path,
                chunk_index=chunk_index,
                total_chunks=0  # Will be set after all chunks are created
            )
            chunks.append(chunk)
            chunk_index += 1

        # Set total_chunks for all chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)

        return chunks

    def _generate_document_id(self, file_path: Path) -> str:
        """Generate a unique document ID"""
        file_hash = hashlib.md5(str(file_path).encode()).hexdigest()[:8]
        return f"doc_{file_hash}"

    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type from file extension"""
        ext = file_path.suffix.lower()
        mime_types = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel',
            '.py': 'text/x-python',
            '.js': 'application/javascript',
            '.java': 'text/x-java-source',
            '.cpp': 'text/x-c++src',
            '.c': 'text/x-csrc',
            '.html': 'text/html',
            '.css': 'text/css',
            '.json': 'application/json',
            '.xml': 'application/xml'
        }
        return mime_types.get(ext, 'application/octet-stream')

    def _load_metadata(self):
        """Load document metadata from disk"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for doc_data in data.get('documents', []):
                        doc_info = DocumentInfo(**doc_data)
                        self.documents[doc_info.id] = doc_info
            except Exception as e:
                print(f"Failed to load document metadata: {e}")

    def _save_metadata(self):
        """Save document metadata to disk"""
        try:
            data = {
                'documents': [doc.__dict__ for doc in self.documents.values()]
            }
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Failed to save document metadata: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get document store statistics"""
        total_docs = len(self.documents)
        completed_docs = sum(1 for doc in self.documents.values() if doc.status == 'completed')
        total_chunks = sum(doc.chunks_count for doc in self.documents.values())

        return {
            'total_documents': total_docs,
            'completed_documents': completed_docs,
            'failed_documents': sum(1 for doc in self.documents.values() if doc.status == 'failed'),
            'total_chunks': total_chunks,
            'embedding_provider': self.config.get('embedding', {}).get('provider', 'none'),
            'vector_backend': self.config.get('vector', {}).get('backend', 'none')
        }

