import aiohttp
import asyncio
import json
from typing import Dict, Any, Optional, List
from .base_provider import BaseProvider


class OllamaProvider(BaseProvider):
    """Ollama provider for running LLMs locally and offline"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'http://localhost:11434').rstrip('/')
        self.model = config.get('model', 'llama2')
        self.timeout = config.get('timeout', 120)  # Ollama can be slow for large models

    async def _make_request(self, prompt: str, system_prompt: Optional[str] = None,
                           stream: bool = True) -> str:
        """Make request to Ollama API"""
        url = f"{self.base_url}/api/generate"

        # Build request payload
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(url, json=payload) as response:
                    response.raise_for_status()

                    if stream:
                        # Handle streaming response
                        buffer = ""
                        async for line in response.content:
                            if line:
                                try:
                                    line_str = line.decode('utf-8').strip()
                                    if line_str:
                                        data = json.loads(line_str)
                                        if chunk := data.get('response'):
                                            buffer += chunk
                                            yield chunk

                                        # Check if this is the final response
                                        if data.get('done', False):
                                            break
                                except json.JSONDecodeError:
                                    continue

                        if not buffer:
                            raise Exception("No content received from Ollama API")
                    else:
                        # Handle non-streaming response
                        data = await response.json()
                        yield data.get('response', '')

        except aiohttp.ClientConnectorError:
            raise Exception(f"Cannot connect to Ollama at {self.base_url}. Make sure Ollama is running and accessible.")
        except aiohttp.ClientTimeout:
            raise Exception(f"Request to Ollama timed out after {self.timeout} seconds")
        except aiohttp.ClientError as e:
            raise Exception(f"Ollama API request failed: {str(e)}")

    async def _check_connection(self) -> bool:
        """Check if Ollama server is accessible and model is available"""
        try:
            url = f"{self.base_url}/api/tags"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [model['name'] for model in data.get('models', [])]
                        return self.model in models
                    return False
        except Exception:
            return False

    async def generate_text(self, prompt: str, model: str = None,
                          system_prompt: Optional[str] = None) -> str:
        """Generate text using Ollama model"""
        if model and model != self.model:
            # For Ollama, we could potentially switch models, but let's keep it simple for now
            print(f"[OLLAMA] Warning: Requested model '{model}' differs from configured '{self.model}'. Using configured model.")

        # Check connection first
        if not await self._check_connection():
            raise Exception(f"Ollama model '{self.model}' not available at {self.base_url}. Make sure Ollama is running and the model is pulled.")

        response_stream = self._make_request(prompt, system_prompt, stream=True)
        response_text = ""

        try:
            async for chunk in response_stream:
                response_text += chunk
        except Exception as e:
            raise Exception(f"Ollama text generation failed: {str(e)}")

        return response_text

    async def generate_code(self, prompt: str, language: Optional[str] = None) -> str:
        """Generate code using Ollama model"""
        system_prompt = (
            f"You are an expert programmer. Generate clean, efficient, and well-documented code{' in ' + language if language else ''}. "
            "Focus on best practices, proper error handling, and clear variable naming."
        )

        return await self.generate_text(prompt, system_prompt=system_prompt)

    async def analyze_code(self, code: str, question: str) -> str:
        """Analyze code using Ollama model"""
        prompt = f"""
Code to analyze:
```
{code}
```

Question: {question}

Please provide a detailed analysis focusing on:
- Code quality and best practices
- Potential bugs or issues
- Performance considerations
- Suggestions for improvement
"""

        system_prompt = (
            "You are an expert code analyst. Provide clear, accurate, and detailed analysis of code. "
            "Focus on best practices, potential issues, improvements, and explain your reasoning."
        )

        return await self.generate_text(prompt, system_prompt=system_prompt)

    async def get_available_models(self) -> List[str]:
        """Get list of available models from Ollama"""
        try:
            url = f"{self.base_url}/api/tags"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [model['name'] for model in data.get('models', [])]
                    return []
        except Exception:
            return []

    @property
    def supported_models(self) -> List[str]:
        """Return list of supported models (dynamically fetched from Ollama)"""
        # Note: This is a sync property, so we can't async fetch here
        # In practice, this would need to be called differently or cached
        return [self.model]  # Return configured model as minimum
