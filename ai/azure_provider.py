import os
import json
import aiohttp
import asyncio
from typing import Dict, Any, Optional, List
from .base_provider import BaseProvider

class AzureProvider(BaseProvider):
    """Azure OpenAI provider with support for DeepSeek and Claude models"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.endpoint = config['endpoint'].rstrip('/')
        self.api_key = config.get('api_key') or os.getenv('AZURE_OPENAI_API_KEY')
        self.api_version = config.get('api_version', '2024-02-15-preview')
        self.models = config.get('models', {})
        
        if not self.api_key:
            raise ValueError("Azure API key not found in config or environment variables")
    
    async def _make_request(self, deployment_name: str, messages: List[Dict[str, str]], 
                          model_config: Dict[str, Any]) -> str:
        """Make request to Azure API endpoint"""
        headers = {
            'api-key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        # Build request URL
        url = f"{self.endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version={self.api_version}"
        
        # Build request body
        body = {
            'messages': messages,
            'max_tokens': model_config.get('max_tokens', 4096),
            'temperature': model_config.get('temperature', 0.7),
            'model': model_config.get('model_name'),  # Required for some models
            'stream': True  # Enable streaming
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=body) as response:
                    response.raise_for_status()
                    
                    # Handle streaming response
                    buffer = ""
                    async for line in response.content:
                        if line:
                            try:
                                line = line.decode('utf-8').strip()
                                if line.startswith('data: ') and line != 'data: [DONE]':
                                    data = json.loads(line[6:])
                                    if choices := data.get('choices'):
                                        if delta := choices[0].get('delta'):
                                            if content := delta.get('content'):
                                                buffer += content
                                                yield content
                            except Exception as e:
                                print(f"Error parsing streaming response: {e}")
                                continue
                    
                    if not buffer:
                        raise Exception("No content received from API")
                        
        except aiohttp.ClientError as e:
            raise Exception(f"Azure API request failed: {str(e)}")
    
    async def generate_text(self, prompt: str, model: str = "deepseek", 
                          system_prompt: Optional[str] = None) -> str:
        """Generate text using specified model"""
        if model not in self.models:
            raise ValueError(f"Model {model} not found in configuration")
            
        model_config = self.models[model]
        deployment_name = model_config['deployment_name']
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({
                'role': 'system',
                'content': system_prompt
            })
        
        messages.append({
            'role': 'user',
            'content': prompt
        })
        
        # Make streaming request
        response_stream = self._make_request(deployment_name, messages, model_config)
        response_text = ""
        
        try:
            async for chunk in response_stream:
                response_text += chunk
                # You can implement progress callback here if needed
                
        except Exception as e:
            raise Exception(f"Text generation failed: {str(e)}")
            
        return response_text
    
    async def generate_code(self, prompt: str, language: Optional[str] = None) -> str:
        """Generate code using DeepSeek model"""
        # Use DeepSeek by default for code generation
        system_prompt = (
            "You are an expert programmer. Generate clean, efficient, and well-documented code. "
            f"Use {language} programming language." if language else 
            "You are an expert programmer. Generate clean, efficient, and well-documented code."
        )
        
        return await self.generate_text(prompt, model="deepseek", system_prompt=system_prompt)
    
    async def analyze_code(self, code: str, question: str) -> str:
        """Analyze code using Claude model"""
        prompt = f"""
        Code to analyze:
        ```
        {code}
        ```
        
        Question: {question}
        
        Please provide a detailed analysis.
        """
        
        system_prompt = (
            "You are an expert code analyst. Provide clear, accurate, and detailed analysis of code. "
            "Focus on best practices, potential issues, and improvements."
        )
        
        return await self.generate_text(prompt, model="claude", system_prompt=system_prompt)
    
    @property
    def supported_models(self) -> List[str]:
        """Return list of supported models"""
        return list(self.models.keys()) 