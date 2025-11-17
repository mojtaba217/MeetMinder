from typing import Dict, Any, Optional
from .base_provider import BaseProvider
from .azure_provider import AzureProvider
from .ollama_provider import OllamaProvider

class AIProviderFactory:
    """Factory for creating AI providers"""
    
    @staticmethod
    def create_provider(provider_type: str, config: Dict[str, Any]) -> BaseProvider:
        """Create and return an AI provider instance"""
        if provider_type == "azure":
            return AzureProvider(config)
        elif provider_type == "ollama":
            return OllamaProvider(config)
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")
    
    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> Optional[BaseProvider]:
        """Create provider from configuration dictionary"""
        for provider_name, provider_config in config.get('providers', {}).items():
            if provider_config.get('enabled', False):
                return AIProviderFactory.create_provider(provider_name, provider_config)
        
        raise ValueError("No enabled AI provider found in configuration") 