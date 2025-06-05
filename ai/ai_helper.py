from openai import AzureOpenAI
from typing import List, Dict, Any, AsyncGenerator, Optional
import asyncio
import time
import threading
import os
import hashlib
import json
from functools import lru_cache
from dataclasses import dataclass
from collections import defaultdict
from core.config import AIProviderConfig, AssistantConfig

@dataclass
class RequestCache:
    """Cache for AI requests to reduce redundant calls"""
    cache: Dict[str, Any]
    timestamps: Dict[str, float]
    max_age: float = 300.0  # 5 minutes
    max_size: int = 100
    
    def __init__(self):
        self.cache = {}
        self.timestamps = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached response if still valid"""
        if key in self.cache:
            if time.time() - self.timestamps[key] < self.max_age:
                return self.cache[key]
            else:
                # Expired, remove
                del self.cache[key]
                del self.timestamps[key]
        return None
    
    def set(self, key: str, value: Any):
        """Cache a response"""
        # Clean old entries if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.timestamps.keys(), key=lambda k: self.timestamps[k])
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]
        
        self.cache[key] = value
        self.timestamps[key] = time.time()

@dataclass  
class RateLimiter:
    """Rate limiter for AI requests"""
    requests: List[float]
    max_requests: int = 60  # per minute
    window: float = 60.0  # 1 minute window
    
    def __init__(self):
        self.requests = []
        self._lock = threading.Lock()
    
    def can_make_request(self) -> bool:
        """Check if we can make a request without hitting rate limits"""
        with self._lock:
            now = time.time()
            # Remove old requests outside window
            self.requests = [req_time for req_time in self.requests if now - req_time < self.window]
            return len(self.requests) < self.max_requests
    
    def record_request(self):
        """Record a new request"""
        with self._lock:
            self.requests.append(time.time())

class AIHelper:
    def __init__(self, config: AIProviderConfig, profile_manager=None, topic_manager=None, config_manager=None):
        self.config = config
        self.profile_manager = profile_manager
        self.topic_manager = topic_manager
        self.config_manager = config_manager
        self.client = None
        self.assistant_config = None
        self.custom_prompt_rules = ""
        
        # Performance optimizations
        self.request_cache = RequestCache()
        self.rate_limiter = RateLimiter()
        self.connection_pool_size = 3
        self.clients_pool = []
        self.pool_lock = threading.Lock()
        
        # Performance metrics
        self.request_metrics = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'rate_limited': 0,
            'avg_response_time': 0.0,
            'last_response_times': []
        }
        
        # Load assistant configuration
        if config_manager:
            self.assistant_config = config_manager.get_assistant_config()
            self.custom_prompt_rules = config_manager.load_prompt_rules()
        
        self._setup_client()
        self._initialize_connection_pool()
    
    def _setup_client(self):
        """Initialize the appropriate AI client based on configuration"""
        if self.config.type == "azure_openai":
            # Create Azure OpenAI client with the proper interface
            self.client = AzureOpenAI(
                api_key=self.config.azure_openai['api_key'],
                api_version=self.config.azure_openai['api_version'],
                azure_endpoint=self.config.azure_openai['endpoint']
            )
            print(f"✅ Azure OpenAI client initialized with model: {self.config.model}")
        elif self.config.type == "google_gemini":
            import google.generativeai as genai
            genai.configure(api_key=self.config.google_gemini['api_key'])
            self.client = genai.GenerativeModel(self.config.google_gemini['model'])
            print(f"✅ Google Gemini client initialized")
        else:
            raise ValueError(f"Unsupported AI provider: {self.config.type}")
    
    def _initialize_connection_pool(self):
        """Initialize a pool of connections for better performance"""
        with self.pool_lock:
            for _ in range(self.connection_pool_size):
                if self.config.type == "azure_openai":
                    client = AzureOpenAI(
                        api_key=self.config.azure_openai['api_key'],
                        api_version=self.config.azure_openai['api_version'],
                        azure_endpoint=self.config.azure_openai['endpoint']
                    )
                    self.clients_pool.append(client)
    
    def _get_client(self):
        """Get a client from the pool"""
        with self.pool_lock:
            if self.clients_pool:
                return self.clients_pool.pop()
            else:
                # Create new client if pool is empty
                if self.config.type == "azure_openai":
                    return AzureOpenAI(
                        api_key=self.config.azure_openai['api_key'],
                        api_version=self.config.azure_openai['api_version'],
                        azure_endpoint=self.config.azure_openai['endpoint']
                    )
                return self.client
    
    def _return_client(self, client):
        """Return client to pool"""
        with self.pool_lock:
            if len(self.clients_pool) < self.connection_pool_size:
                self.clients_pool.append(client)
    
    def _generate_cache_key(self, prompt: str, config: Dict[str, Any]) -> str:
        """Generate cache key for request"""
        cache_data = {
            'prompt': prompt[:200],  # First 200 chars to avoid huge keys
            'model': self.config.model,
            'temperature': config.get('temperature', 0.7),
            'max_tokens': config.get('max_tokens', 500)
        }
        return hashlib.md5(json.dumps(cache_data, sort_keys=True).encode()).hexdigest()
    
    async def analyze_context_stream(self, 
                                   transcript: List[str], 
                                   screen_context: str,
                                   clipboard_content: str = None,
                                   context_type: str = "general") -> AsyncGenerator[str, None]:
        """Stream real-time AI analysis of context with enhanced dual-stream support and caching"""
        
        # Check rate limiting
        if not self.rate_limiter.can_make_request():
            self.request_metrics['rate_limited'] += 1
            yield "Rate limit reached. Please wait before making another request."
            return
        
        context_prompt = self._build_context_prompt(
            transcript, screen_context, clipboard_content, context_type
        )
        
        # Check cache first for non-streaming requests
        cache_key = self._generate_cache_key(context_prompt, {
            'temperature': self._get_temperature(),
            'max_tokens': self._get_max_tokens()
        })
        
        cached_response = self.request_cache.get(cache_key)
        if cached_response:
            self.request_metrics['cache_hits'] += 1
            # Stream cached response
            for chunk in cached_response:
                yield chunk
                await asyncio.sleep(0.01)
            return
        
        self.request_metrics['cache_misses'] += 1
        self.rate_limiter.record_request()
        self.request_metrics['total_requests'] += 1
        
        start_time = time.time()
        response_chunks = []
        
        try:
            if self.config.type == "azure_openai":
                async for chunk in self._stream_azure_openai(context_prompt):
                    response_chunks.append(chunk)
                    yield chunk
            elif self.config.type == "google_gemini":
                async for chunk in self._stream_google_gemini(context_prompt):
                    response_chunks.append(chunk)
                    yield chunk
            
            # Cache the response
            self.request_cache.set(cache_key, response_chunks)
            
            # Update performance metrics
            response_time = time.time() - start_time
            self.request_metrics['last_response_times'].append(response_time)
            if len(self.request_metrics['last_response_times']) > 10:
                self.request_metrics['last_response_times'].pop(0)
            
            self.request_metrics['avg_response_time'] = sum(
                self.request_metrics['last_response_times']
            ) / len(self.request_metrics['last_response_times'])
                    
        except Exception as e:
            yield f"Error: AI analysis failed - {e}"
    
    async def _stream_azure_openai(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream responses from Azure OpenAI with configurable model"""
        try:
            # Use model from environment or config
            model_name = self.config.model
            
            # Prepare the parameters for the API call
            params = {
                "model": self.config.azure_openai.get('deployment_name', model_name),
                "messages": [
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self._get_temperature(),
                "max_tokens": self._get_max_tokens(),
                "stream": True
            }
            
            # Run the synchronous Azure OpenAI call in a thread
            def run_completion():
                return self.client.chat.completions.create(**params)
            
            # Execute in thread to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, run_completion)
            
            # Stream the response chunks
            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        yield delta.content
                        # Small delay to allow UI updates
                        await asyncio.sleep(0.01)
                        
        except Exception as e:
            yield f"Azure OpenAI Error: {e}"
    
    async def _stream_google_gemini(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream responses from Google Gemini"""
        try:
            full_prompt = f"{self._get_system_prompt()}\n\n{prompt}"
            
            # Run Gemini generation in thread
            def run_generation():
                return self.client.generate_content(
                    full_prompt,
                    stream=True,
                    generation_config={
                        'temperature': self._get_temperature(), 
                        'max_output_tokens': self._get_max_tokens()
                    }
                )
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, run_generation)
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    await asyncio.sleep(0.01)  # Small delay for streaming effect
                    
        except Exception as e:
            yield f"Google Gemini Error: {e}"
    
    def _get_temperature(self) -> float:
        """Get temperature based on assistant configuration"""
        if not self.assistant_config:
            return 0.7
        
        temp_map = {
            "concise": 0.3,
            "standard": 0.7,
            "detailed": 0.9
        }
        return temp_map.get(self.assistant_config.verbosity, 0.7)
    
    def _get_max_tokens(self) -> int:
        """Get max tokens based on assistant configuration"""
        if not self.assistant_config:
            return 500
        
        token_map = {
            "concise": 200,
            "standard": 500,
            "detailed": 800
        }
        return token_map.get(self.assistant_config.verbosity, 500)
    
    def _build_context_prompt(self, 
                            transcript: List[str], 
                            screen_context: str, 
                            clipboard_content: str,
                            context_type: str) -> str:
        """Build context-aware prompt with enhanced dual-stream support"""
        
        # Get user profile summary
        profile_summary = ""
        if self.profile_manager:
            profile_summary = self.profile_manager.get_profile_summary()
        
        # Get topic matches and suggestions
        topic_guidance = ""
        if self.topic_manager and transcript:
            # Handle both single-stream and dual-stream transcripts
            if transcript and any('[USER]' in t or '[SYSTEM]' in t for t in transcript):
                # Dual-stream format - extract text without tags for topic matching
                combined_text = " ".join([
                    t.split('] ', 1)[1] if '] ' in t else t 
                    for t in transcript[-3:]
                ])
            else:
                # Single-stream format
                combined_text = " ".join(transcript[-3:])
            
            matches = self.topic_manager.match_topics(combined_text)
            if matches:
                suggestions = self.topic_manager.get_topic_suggestions(matches)
                topic_guidance = "\n".join(suggestions[:2])  # Top 2 suggestions
        
        # Detect if we have dual-stream data
        has_dual_stream = transcript and any('[USER]' in t or '[SYSTEM]' in t for t in transcript)
        
        # Separate and prioritize dual-stream content
        user_content = []
        system_content = []
        
        if has_dual_stream:
            for entry in transcript:
                if '[USER]' in entry:
                    user_content.append(entry.replace('[USER] ', ''))
                elif '[SYSTEM]' in entry:
                    system_content.append(entry.replace('[SYSTEM] ', ''))
        
        # Apply input prioritization from assistant config
        prioritized_content = self._prioritize_audio_content(user_content, system_content)
        
        context_templates = {
            "meeting": f"""
MEETING CONTEXT {"(Dual Audio Stream)" if has_dual_stream else ""}:
User Profile: {{profile}}
{"Prioritized Content: " + prioritized_content if has_dual_stream else "Recent Conversation: " + str(transcript)}
Active Window: {{screen_context}}
Topic Guidance: {{topic_guidance}}

{"DUAL STREAM ANALYSIS - System audio (meeting) prioritized:" if has_dual_stream else "Provide brief, actionable meeting assistance:"}
1. {"Focus on system audio content (what others are saying) for primary context" if has_dual_stream else "Summarize key points from the conversation"}
2. {"Use user voice to understand questions, reactions, or intended responses" if has_dual_stream else "Suggest 2-3 relevant responses or questions based on user's background"}
3. {"Provide meeting assistance based on combined understanding" if has_dual_stream else "Identify any action items or decisions needed"}
4. Consider topic guidance for conversation direction

Response Style: {self.assistant_config.response_style if self.assistant_config else "professional"}
            """,
            "coding": f"""
CODING CONTEXT {"(Dual Audio Stream)" if has_dual_stream else ""}:
User Profile: {{profile}}
{"Prioritized Content: " + prioritized_content if has_dual_stream else "Recent Audio: " + str(transcript)}
Active Window: {{screen_context}}
Clipboard: {{clipboard}}
Topic Guidance: {{topic_guidance}}

{"DUAL STREAM ANALYSIS - System audio prioritized for learning content:" if has_dual_stream else "Provide coding assistance based on user's skills:"}
1. {"Analyze system audio for tutorial/educational content being consumed" if has_dual_stream else "Analyze current context and user's experience level"}
2. {"Use user voice to understand questions or confusion points" if has_dual_stream else "Suggest code improvements or solutions"}
3. {"Provide coding guidance that bridges tutorial content with user's questions" if has_dual_stream else "Recommend next steps or debugging approaches"}
4. Use knowledge of user's background in recommendations

Response Style: {self.assistant_config.response_style if self.assistant_config else "professional"}
            """,
            "general": f"""
GENERAL CONTEXT {"(Dual Audio Stream)" if has_dual_stream else ""}:
User Profile: {{profile}}
{"Prioritized Content: " + prioritized_content if has_dual_stream else "Recent Audio: " + str(transcript)}
Screen Context: {{screen_context}}
Clipboard: {{clipboard}}
Topic Guidance: {{topic_guidance}}

{"DUAL STREAM ANALYSIS - System audio prioritized:" if has_dual_stream else "Provide helpful assistance:"}
1. {"Primary focus: System audio content (what user is listening to/watching)" if has_dual_stream else "Analyze the current situation considering user's background"}
2. {"Secondary focus: User voice for questions, reactions, or clarifications" if has_dual_stream else "Suggest 2-3 practical next steps relevant to user's skills"}
3. {"Provide assistance that connects external content with user's needs" if has_dual_stream else "Offer relevant tips or information based on user's experience"}
4. Consider topic guidance for additional context

Response Style: {self.assistant_config.response_style if self.assistant_config else "professional"}
            """
        }
        
        template = context_templates.get(context_type, context_templates["general"])
        
        # Format transcript for better readability
        formatted_transcript = self._format_transcript_for_ai(transcript)
        
        return template.format(
            profile=profile_summary or "No profile information",
            transcript=formatted_transcript or "No recent audio",
            screen_context=screen_context or "Unknown",
            clipboard=clipboard_content[:200] if clipboard_content else "Empty",
            topic_guidance=topic_guidance or "No specific topic guidance"
        )
    
    def _prioritize_audio_content(self, user_content: List[str], system_content: List[str]) -> str:
        """Prioritize audio content based on assistant configuration"""
        if not self.assistant_config:
            # Default: system audio priority
            return f"System Audio: {' '.join(system_content[-3:])} | User Voice: {' '.join(user_content[-2:])}"
        
        if self.assistant_config.input_prioritization == "system_audio":
            # System audio first (default for meetings, learning)
            return f"🔊 System Audio (Primary): {' '.join(system_content[-3:])} | 🎤 User Voice: {' '.join(user_content[-2:])}"
        elif self.assistant_config.input_prioritization == "mic":
            # Microphone first (for dictation, personal notes)
            return f"🎤 User Voice (Primary): {' '.join(user_content[-3:])} | 🔊 System Audio: {' '.join(system_content[-2:])}"
        else:  # balanced
            # Balanced approach
            combined = []
            max_len = max(len(user_content), len(system_content))
            for i in range(max_len):
                if i < len(system_content):
                    combined.append(f"🔊 {system_content[i]}")
                if i < len(user_content):
                    combined.append(f"🎤 {user_content[i]}")
            return " | ".join(combined[-5:])  # Last 5 entries
    
    def _format_transcript_for_ai(self, transcript: List[str]) -> str:
        """Format transcript for better AI understanding"""
        if not transcript:
            return "No recent audio"
        
        # Handle dual-stream format
        if any('[USER]' in t or '[SYSTEM]' in t for t in transcript):
            formatted = []
            for entry in transcript[-5:]:  # Last 5 entries
                if '[USER]' in entry:
                    formatted.append(f"👤 User: {entry.replace('[USER] ', '')}")
                elif '[SYSTEM]' in entry:
                    formatted.append(f"🔊 System: {entry.replace('[SYSTEM] ', '')}")
                else:
                    formatted.append(f"📝 {entry}")
            return "\n".join(formatted)
        else:
            # Single-stream format
            return "\n".join([f"📝 {entry}" for entry in transcript[-5:]])
    
    def _get_system_prompt(self) -> str:
        """Get system prompt with custom rules integration"""
        base_prompt = """You are an intelligent AI assistant providing real-time contextual help. You analyze conversation transcripts, screen context, and user profiles to provide relevant, actionable assistance.

Key Capabilities:
- Real-time conversation analysis with dual audio stream support
- Context-aware suggestions based on user background
- Topic-guided assistance using knowledge graphs
- Meeting, coding, and learning context specialization

Response Guidelines:
- Be concise but comprehensive
- Provide actionable next steps
- Consider user's expertise level
- Prioritize system audio content in dual-stream scenarios
- Use structured formatting for clarity"""

        # Add custom prompt rules if available
        if self.custom_prompt_rules:
            base_prompt += f"\n\nCUSTOM RULES AND GUIDELINES:\n{self.custom_prompt_rules}"
        
        # Add assistant configuration context
        if self.assistant_config:
            config_context = f"""

ASSISTANT CONFIGURATION:
- Activation Mode: {self.assistant_config.activation_mode}
- Verbosity: {self.assistant_config.verbosity}
- Response Style: {self.assistant_config.response_style}
- Input Priority: {self.assistant_config.input_prioritization}

Adjust your responses according to these settings."""
            base_prompt += config_context
        
        return base_prompt
    
    def update_config(self, new_config: AIProviderConfig):
        """Update AI configuration"""
        self.config = new_config
        self._setup_client()
    
    def update_assistant_config(self, new_assistant_config: AssistantConfig):
        """Update assistant configuration"""
        self.assistant_config = new_assistant_config
        print(f"✅ Updated assistant config: {new_assistant_config.response_style} style, {new_assistant_config.verbosity} verbosity") 