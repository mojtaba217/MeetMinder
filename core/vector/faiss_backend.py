"""
FAISS vector backend for offline document storage
"""

import asyncio
import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from ..document_store import VectorBackend, DocumentChunk

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

class FAISSBackend(VectorBackend):
    """FAISS-based vector storage for offline use"""

    def __init__(self, config: Dict[str, Any], data_dir: Path):
        if not FAISS_AVAILABLE:
            raise ImportError(
                "faiss-cpu not installed. Install with: pip install faiss-cpu"
            )

        self.config = config
        self.data_dir = data_dir
        self.data_dir.mkdir(exist_ok=True)

        # File paths
        self.index_file = data_dir / 'faiss_index.faiss'
        self.metadata_file = data_dir / 'faiss_metadata.pkl'

        # FAISS index and metadata storage
        self.index: Optional[faiss.Index] = None
        self.chunk_metadata: Dict[int, DocumentChunk] = {}
        self.id_to_index: Dict[str, int] = {}
        self.next_id = 0

        # Configuration
        self.dimension = config.get('dimension', 384)  # Default for sentence-transformers
        self.metric = config.get('metric', 'cosine')  # cosine, l2, ip

    async def initialize(self) -> bool:
        """Initialize FAISS index"""
        try:
            if self.metric == 'cosine':
                # For cosine similarity, we use IndexFlatIP (inner product) with normalized vectors
                self.index = faiss.IndexFlatIP(self.dimension)
            elif self.metric == 'l2':
                self.index = faiss.IndexFlatL2(self.dimension)
            elif self.metric == 'ip':
                self.index = faiss.IndexFlatIP(self.dimension)
            else:
                raise ValueError(f"Unsupported metric: {self.metric}")

            return True
        except Exception as e:
            print(f"Failed to initialize FAISS index: {e}")
            return False

    async def upsert(self, chunk: DocumentChunk) -> bool:
        """Store a document chunk"""
        try:
            if not self.index:
                await self.initialize()

            if not chunk.embedding is None:
                raise ValueError("Chunk must have embedding")

            # Convert to 2D array for FAISS
            embedding = chunk.embedding.reshape(1, -1)

            # Normalize for cosine similarity
            if self.metric == 'cosine':
                faiss.normalize_L2(embedding)

            # Add to index
            self.index.add(embedding.astype(np.float32))

            # Store metadata
            chunk_id = self.next_id
            self.chunk_metadata[chunk_id] = chunk
            self.id_to_index[chunk.id] = chunk_id
            self.next_id += 1

            return True
        except Exception as e:
            print(f"Failed to upsert chunk {chunk.id}: {e}")
            return False

    async def search(self, query_embedding: np.ndarray, top_k: int = 5,
                    filter_dict: Optional[Dict[str, Any]] = None) -> List[Tuple[DocumentChunk, float]]:
        """Search for similar chunks"""
        try:
            if not self.index or self.index.ntotal == 0:
                return []

            # Prepare query embedding
            query = query_embedding.reshape(1, -1)

            # Normalize for cosine similarity
            if self.metric == 'cosine':
                faiss.normalize_L2(query)

            # Search
            scores, indices = self.index.search(query.astype(np.float32), min(top_k, self.index.ntotal))

            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:  # FAISS returns -1 for no results
                    continue

                chunk = self.chunk_metadata.get(idx)
                if not chunk:
                    continue

                # Apply filters if provided
                if filter_dict:
                    skip = False
                    for key, value in filter_dict.items():
                        if chunk.metadata.get(key) != value:
                            skip = True
                            break
                    if skip:
                        continue

                # Convert distance to similarity score
                if self.metric == 'cosine':
                    similarity = float(score)  # Already cosine similarity
                elif self.metric == 'l2':
                    similarity = 1.0 / (1.0 + float(score))  # Convert L2 distance to similarity
                else:  # ip (inner product)
                    similarity = float(score)

                results.append((chunk, similarity))

            # Sort by similarity (descending)
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]

        except Exception as e:
            print(f"Search failed: {e}")
            return []

    async def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a document"""
        try:
            # Find all chunk IDs for this document
            chunks_to_delete = []
            for chunk_id, chunk in self.chunk_metadata.items():
                if chunk.metadata.get('document_id') == document_id:
                    chunks_to_delete.append(chunk_id)

            if not chunks_to_delete:
                return True

            # FAISS doesn't support deletion, so we need to rebuild the index
            # This is a limitation of FAISS - for production, consider using a different backend
            print(f"Warning: FAISS doesn't support deletion. {len(chunks_to_delete)} chunks marked as deleted but index not rebuilt.")

            # Mark chunks as deleted (you could implement a tombstone system)
            for chunk_id in chunks_to_delete:
                if chunk_id in self.chunk_metadata:
                    del self.chunk_metadata[chunk_id]
                # Remove from id_to_index
                chunk_id_to_remove = None
                for cid, idx in self.id_to_index.items():
                    if idx == chunk_id:
                        chunk_id_to_remove = cid
                        break
                if chunk_id_to_remove:
                    del self.id_to_index[chunk_id_to_remove]

            # Note: In a production system, you'd want to rebuild the FAISS index
            # For now, we'll just mark as deleted and save the updated metadata
            await self.save()
            return True

        except Exception as e:
            print(f"Failed to delete document {document_id}: {e}")
            return False

    async def get_document_chunks(self, document_id: str) -> List[DocumentChunk]:
        """Get all chunks for a document"""
        chunks = []
        for chunk in self.chunk_metadata.values():
            if chunk.metadata.get('document_id') == document_id:
                chunks.append(chunk)
        return chunks

    async def save(self) -> bool:
        """Persist index and metadata to disk"""
        try:
            # Save FAISS index
            if self.index:
                faiss.write_index(self.index, str(self.index_file))

            # Save metadata
            metadata = {
                'chunk_metadata': self.chunk_metadata,
                'id_to_index': self.id_to_index,
                'next_id': self.next_id,
                'dimension': self.dimension,
                'metric': self.metric
            }

            with open(self.metadata_file, 'wb') as f:
                pickle.dump(metadata, f)

            return True
        except Exception as e:
            print(f"Failed to save FAISS data: {e}")
            return False

    async def load(self) -> bool:
        """Load index and metadata from disk"""
        try:
            # Load metadata first
            if self.metadata_file.exists():
                with open(self.metadata_file, 'rb') as f:
                    metadata = pickle.load(f)

                self.chunk_metadata = metadata.get('chunk_metadata', {})
                self.id_to_index = metadata.get('id_to_index', {})
                self.next_id = metadata.get('next_id', 0)
                self.dimension = metadata.get('dimension', self.dimension)
                self.metric = metadata.get('metric', self.metric)

            # Load FAISS index
            if self.index_file.exists():
                if self.metric == 'cosine':
                    self.index = faiss.read_index(str(self.index_file))
                elif self.metric == 'l2':
                    self.index = faiss.read_index(str(self.index_file))
                elif self.metric == 'ip':
                    self.index = faiss.read_index(str(self.index_file))
            else:
                # Initialize empty index
                await self.initialize()

            return True
        except Exception as e:
            print(f"Failed to load FAISS data: {e}")
            # Try to initialize fresh
            await self.initialize()
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get backend statistics"""
        return {
            'total_vectors': self.index.ntotal if self.index else 0,
            'total_chunks': len(self.chunk_metadata),
            'dimension': self.dimension,
            'metric': self.metric,
            'index_file_exists': self.index_file.exists(),
            'metadata_file_exists': self.metadata_file.exists()
        }

    async def rebuild_index(self) -> bool:
        """Rebuild the FAISS index (useful after many deletions)"""
        try:
            # Collect all current chunks
            current_chunks = list(self.chunk_metadata.values())

            if not current_chunks:
                # Just reinitialize empty index
                await self.initialize()
                return True

            # Create new index
            old_dimension = self.dimension
            old_metric = self.metric
            await self.initialize()

            # Re-add all chunks
            for chunk in current_chunks:
                if chunk.embedding is not None:
                    await self.upsert(chunk)

            await self.save()
            return True

        except Exception as e:
            print(f"Failed to rebuild index: {e}")
            return False

