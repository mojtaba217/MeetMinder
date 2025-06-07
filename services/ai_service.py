"""
AI Service abstraction layer for MeetMinder.
Provides unified interface for different AI providers.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import asyncio
import logging
from dataclasses import dataclass

try:
    import openai
except ImportError:
    openai = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from utils.error_handler import AIServiceError, handle_errors

logger = logging.getLogger('meetminder.ai_service')


@dataclass
class AIRequest:
    """AI request data structure."""
    prompt: str
    context: Optional[str] = None
    system_message: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None


@dataclass
class AIResponse:
    """AI response data structure."""
    content: str
    model: str
    tokens_used: Optional[int] = None
    cost: Optional[float] = None


class AIServiceInterface(ABC):
    """Interface for AI services."""
    
    @abstractmethod
    async def generate_response(self, request: AIRequest) -> AIResponse:
        """Generate AI response for given request."""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        pass
    
    @abstractmethod
    def estimate_cost(self, request: AIRequest) -> float:
        """Estimate cost for request."""
        pass


class OpenAIService(AIServiceInterface):
    """OpenAI service implementation."""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        if openai is None:
            raise ImportError("OpenAI library not installed. Install with: pip install openai")
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.logger = logger
    
    @handle_errors(fallback_return=AIResponse("Sorry, I couldn't process your request.", "error"))
    async def generate_response(self, request: AIRequest) -> AIResponse:
        """Generate response using OpenAI."""
        try:
            messages = []
            
            if request.system_message:
                messages.append({"role": "system", "content": request.system_message})
            
            if request.context:
                messages.append({"role": "system", "content": f"Context: {request.context}"})
            
            messages.append({"role": "user", "content": request.prompt})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else None
            
            self.logger.info(f"OpenAI response generated: {len(content)} chars, {tokens_used} tokens")
            
            return AIResponse(
                content=content,
                model=self.model,
                tokens_used=tokens_used
            )
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise AIServiceError(f"OpenAI service error: {e}")
    
    def get_available_models(self) -> List[str]:
        """Get list of available OpenAI models."""
        return ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"]
    
    def estimate_cost(self, request: AIRequest) -> float:
        """Estimate cost for OpenAI request."""
        # Rough estimation - actual costs vary by model
        estimated_tokens = len(request.prompt.split()) * 1.3
        if self.model.startswith("gpt-4"):
            return estimated_tokens * 0.00003  # $0.03 per 1K tokens
        else:
            return estimated_tokens * 0.000002  # $0.002 per 1K tokens


class GeminiService(AIServiceInterface):
    """Google Gemini service implementation."""
    
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        if genai is None:
            raise ImportError("Google Generative AI library not installed. Install with: pip install google-generativeai")
        genai.configure(api_key=api_key)
        self.model_name = model
        self.model = genai.GenerativeModel(model)
        self.logger = logger
    
    @handle_errors(fallback_return=AIResponse("Sorry, I couldn't process your request.", "error"))
    async def generate_response(self, request: AIRequest) -> AIResponse:
        """Generate response using Gemini."""
        try:
            # Combine system message, context, and prompt
            full_prompt = ""
            if request.system_message:
                full_prompt += f"System: {request.system_message}\n\n"
            if request.context:
                full_prompt += f"Context: {request.context}\n\n"
            full_prompt += request.prompt
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=request.temperature,
                    max_output_tokens=request.max_tokens
                )
            )
            
            content = response.text
            self.logger.info(f"Gemini response generated: {len(content)} chars")
            
            return AIResponse(
                content=content,
                model=self.model_name
            )
            
        except Exception as e:
            self.logger.error(f"Gemini API error: {e}")
            raise AIServiceError(f"Gemini service error: {e}")
    
    def get_available_models(self) -> List[str]:
        """Get list of available Gemini models."""
        return ["gemini-pro", "gemini-pro-vision"]
    
    def estimate_cost(self, request: AIRequest) -> float:
        """Estimate cost for Gemini request."""
        # Gemini has generous free tier
        return 0.0


class AIServiceFactory:
    """Factory for creating AI services."""
    
    @staticmethod
    def create_service(provider: str, **kwargs) -> AIServiceInterface:
        """Create AI service based on provider."""
        provider_lower = provider.lower()
        
        if provider_lower == "openai":
            return OpenAIService(**kwargs)
        elif provider_lower == "gemini":
            return GeminiService(**kwargs)
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")
    
    @staticmethod
    def get_supported_providers() -> List[str]:
        """Get list of supported AI providers."""
        return ["openai", "gemini"]


class AIServiceManager:
    """Manager for AI services with caching and load balancing."""
    
    def __init__(self):
        self.services: Dict[str, AIServiceInterface] = {}
        self.cache: Dict[str, AIResponse] = {}
        self.cache_size = 100
        self.logger = logger
    
    def add_service(self, name: str, service: AIServiceInterface) -> None:
        """Add AI service to manager."""
        self.services[name] = service
        self.logger.info(f"Added AI service: {name}")
    
    def remove_service(self, name: str) -> None:
        """Remove AI service from manager."""
        if name in self.services:
            del self.services[name]
            self.logger.info(f"Removed AI service: {name}")
    
    @handle_errors(fallback_return=AIResponse("Service unavailable", "error"))
    async def generate_response(self, service_name: str, request: AIRequest) -> AIResponse:
        """Generate response using specified service."""
        if service_name not in self.services:
            raise AIServiceError(f"Service not found: {service_name}")
        
        # Check cache
        cache_key = f"{service_name}:{hash(request.prompt + (request.context or ''))}"
        if cache_key in self.cache:
            self.logger.debug(f"Cache hit for request: {cache_key}")
            return self.cache[cache_key]
        
        # Generate response
        service = self.services[service_name]
        response = await service.generate_response(request)
        
        # Cache response
        if len(self.cache) >= self.cache_size:
            # Remove oldest entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[cache_key] = response
        return response
    
    def clear_cache(self) -> None:
        """Clear response cache."""
        self.cache.clear()
        self.logger.info("AI response cache cleared")
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get statistics about AI services."""
        return {
            "services": list(self.services.keys()),
            "cache_size": len(self.cache),
            "cache_capacity": self.cache_size
        } 