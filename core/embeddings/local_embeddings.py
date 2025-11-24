"""
Local embedding provider using sentence-transformers for offline use
"""

import asyncio
from typing import List, Dict, Any
import numpy as np
from ..document_store import EmbeddingProvider

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider using sentence-transformers"""

    # Default model configurations
    MODEL_CONFIGS = {
        'all-MiniLM-L6-v2': {
            'dimensions': 384,
            'size_mb': 23,
            'description': 'Fast, lightweight, good for general use'
        },
        'all-mpnet-base-v2': {
            'dimensions': 768,
            'size_mb': 109,
            'description': 'High quality, slower, better semantic understanding'
        },
        'e5-small-v2': {
            'dimensions': 384,
            'size_mb': 35,
            'description': 'Good balance of speed and quality'
        }
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_name = config.get('model', 'all-MiniLM-L6-v2')
        self.device = config.get('device', 'cpu')  # cpu, cuda, mps
        self.model = None
        self._dimension = self.MODEL_CONFIGS.get(self.model_name, {}).get('dimensions', 384)

        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )

    async def initialize(self) -> bool:
        """Initialize the model"""
        try:
            # Run model loading in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                lambda: SentenceTransformer(self.model_name, device=self.device)
            )
            return True
        except Exception as e:
            print(f"Failed to load sentence-transformers model {self.model_name}: {e}")
            return False

    async def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text"""
        if not self.model:
            await self.initialize()

        if not self.model:
            raise RuntimeError("Model not initialized")

        # Run embedding in thread pool
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            lambda: self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        )
        return embedding

    async def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """Embed multiple texts"""
        if not self.model:
            await self.initialize()

        if not self.model:
            raise RuntimeError("Model not initialized")

        # Run batch embedding in thread pool
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True, batch_size=32)
        )

        # Convert to list of numpy arrays
        if isinstance(embeddings, np.ndarray):
            return [embeddings[i] for i in range(len(embeddings))]
        return embeddings

    @property
    def dimension(self) -> int:
        """Return embedding dimension"""
        return self._dimension

    async def is_available(self) -> bool:
        """Check if provider is available"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            return False

        try:
            if not self.model:
                success = await self.initialize()
                return success
            return True
        except Exception:
            return False

    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """Get information about available models"""
        return self.MODEL_CONFIGS.copy()

    def get_model_info(self) -> Dict[str, Any]:
        """Get current model information"""
        config = self.MODEL_CONFIGS.get(self.model_name, {})
        return {
            'name': self.model_name,
            'dimensions': config.get('dimensions', 384),
            'size_mb': config.get('size_mb', 0),
            'description': config.get('description', ''),
            'device': self.device,
            'loaded': self.model is not None
        }

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        # Cleanup if needed
        pass

