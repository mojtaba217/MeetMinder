from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class BaseProvider(ABC):
    """Base class for AI providers"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize provider with configuration"""
        self.config = config
    
    @abstractmethod
    async def generate_text(self, prompt: str, model: str = None, 
                          system_prompt: Optional[str] = None) -> str:
        """Generate text using specified model"""
        pass
    
    @abstractmethod
    async def generate_code(self, prompt: str, language: Optional[str] = None) -> str:
        """Generate code in specified language"""
        pass
    
    @abstractmethod
    async def analyze_code(self, code: str, question: str) -> str:
        """Analyze code and answer questions about it"""
        pass
    
    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """Return list of supported models"""
        pass 