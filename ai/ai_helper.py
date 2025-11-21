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
from core.document_store import DocumentStore
from .ollama_provider import OllamaProvider

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
    def __init__(self, config: Optional[AIProviderConfig], profile_manager=None, topic_manager=None, config_manager=None):
        self.config = config
        self.profile_manager = profile_manager
        self.topic_manager = topic_manager
        self.config_manager = config_manager
        self.client = None
        self.assistant_config = None
        self.custom_prompt_rules = ""
        self.ai_available = config is not None and config.type not in [None, "", "none"]

        # Initialize document store for RAG
        self.document_store = None
        if config_manager and config_manager.get_document_config().enabled:
            try:
                doc_config = config_manager.get_document_config()
                self.document_store = DocumentStore(doc_config.__dict__)
                # Initialize document store asynchronously
                asyncio.create_task(self._initialize_document_store())
            except Exception as e:
                print(f"Failed to initialize document store: {e}")
                self.document_store = None

        # Performance optimizations - use advanced caching system
        try:
            from utils.performance_manager import performance_manager
            self.request_cache = performance_manager.cache  # Use advanced cache with TTL and LRU
            print("[CACHE] Using advanced performance cache for AI requests")
        except ImportError:
            self.request_cache = RequestCache()  # Fallback to basic cache
            print("[WARN] Using basic cache for AI requests")

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

        if self.ai_available:
            self._setup_client()
            self._initialize_connection_pool()
        else:
            print("[AI] AI provider not configured - transcription-only mode")

    async def _initialize_document_store(self):
        """Initialize the document store asynchronously"""
        if self.document_store:
            success = await self.document_store.initialize()
            if success:
                print("[DOCS] Document store initialized successfully")
                # Migrate existing resume.md if it exists and no documents yet
                if self.config_manager and self.document_store.list_documents() == []:
                    await self._migrate_resume_to_documents()
            else:
                print("[DOCS] Failed to initialize document store")
                self.document_store = None

    async def _migrate_resume_to_documents(self):
        """Migrate existing resume.md to the document store"""
        if not self.config_manager or not self.document_store:
            return

        resume_config = self.config_manager.get('user_profile', {})
        resume_path = resume_config.get('resume_path', 'data/resume.md')

        if Path(resume_path).exists():
            try:
                doc_id = await self.document_store.add_file(resume_path, {
                    'type': 'resume',
                    'auto_migrated': True,
                    'description': 'Auto-migrated resume from legacy system'
                })
                success = await self.document_store.process_document(doc_id)
                if success:
                    print(f"[DOCS] Successfully migrated resume.md to document store (ID: {doc_id})")
                else:
                    print("[DOCS] Failed to process migrated resume.md")
            except Exception as e:
                print(f"[DOCS] Failed to migrate resume.md: {e}")

    def is_available(self) -> bool:
        """Check if AI provider is configured and available"""
        return self.ai_available

    def _setup_client(self):
        """Initialize the appropriate AI client based on configuration"""
        if not self.ai_available:
            return  # Skip client setup for offline mode

        if self.config.type == "azure_openai":
            # Create Azure OpenAI client with the proper interface
            self.client = AzureOpenAI(
                api_key=self.config.azure_openai['api_key'],
                api_version=self.config.azure_openai['api_version'],
                azure_endpoint=self.config.azure_openai['endpoint']
            )
            print(f"[AZURE] Azure OpenAI client initialized with model: {self.config.model}")
        elif self.config.type == "google_gemini":
            import google.generativeai as genai
            genai.configure(api_key=self.config.google_gemini['api_key'])
            self.client = genai.GenerativeModel(self.config.google_gemini['model'])
            print(f"[GEMINI] Google Gemini client initialized")
        elif self.config.type == "ollama":
            # Create Ollama provider instance
            ollama_config = {
                'base_url': self.config.ollama.get('base_url', 'http://localhost:11434'),
                'model': self.config.ollama.get('model', self.config.model),
                'timeout': self.config.ollama.get('timeout', 120)
            }
            self.client = OllamaProvider(ollama_config)
            print(f"[OLLAMA] Ollama client initialized with model: {ollama_config['model']} at {ollama_config['base_url']}")
        else:
            raise ValueError(f"Unsupported AI provider: {self.config.type}")
    
    def _initialize_connection_pool(self):
        """Initialize a pool of connections for better performance"""
        if not self.ai_available:
            return  # Skip pool initialization for offline mode

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

        # Check if AI is available
        if not self.is_available():
            yield "🤖 AI responses disabled - transcription only mode active. Configure an AI provider in config.yaml for intelligent assistance."
            return

        # Check rate limiting
        if not self.rate_limiter.can_make_request():
            self.request_metrics['rate_limited'] += 1
            yield "Rate limit reached. Please wait before making another request."
            return
        
        context_prompt = await self._build_context_prompt(
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
            elif self.config.type == "ollama":
                async for chunk in self._stream_ollama(context_prompt):
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

    async def _stream_ollama(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream responses from Ollama"""
        try:
            system_prompt = self._get_system_prompt()
            async for chunk in self.client._make_request(prompt, system_prompt=system_prompt, stream=True):
                yield chunk
                await asyncio.sleep(0.01)  # Small delay for UI updates

        except Exception as e:
            yield f"Ollama Error: {e}"

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
    
    async def _build_context_prompt(self, 
                            transcript: List[str], 
                            screen_context: str, 
                            clipboard_content: str,
                            context_type: str) -> str:
        """Build context-aware prompt with enhanced dual-stream support"""
        
        # Get user profile summary
        profile_summary = ""
        if self.profile_manager:
            # Try async version first (with document enhancement), fallback to sync
            try:
                import asyncio
                if asyncio.iscoroutinefunction(self.profile_manager.get_profile_summary_async):
                    profile_summary = await self.profile_manager.get_profile_summary_async()
                else:
                    profile_summary = self.profile_manager.get_profile_summary()
            except Exception:
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

        # Get relevant documents from document store
        document_context = await self._get_relevant_documents(transcript, screen_context, clipboard_content, context_type)

        context_templates = {
            "meeting": f"""
MEETING CONTEXT {"(Dual Audio Stream)" if has_dual_stream else ""}:
User Profile: {{profile}}
{"Prioritized Content: " + prioritized_content if has_dual_stream else "Recent Conversation: " + str(transcript)}
Active Window: {{screen_context}}
Topic Guidance: {{topic_guidance}}
Document Context: {{document_context}}

{"DUAL STREAM ANALYSIS - System audio (meeting) prioritized:" if has_dual_stream else "Provide brief, actionable meeting assistance:"}
1. {"Focus on system audio content (what others are saying) for primary context" if has_dual_stream else "Summarize key points from the conversation"}
2. {"Use user voice to understand questions, reactions, or intended responses" if has_dual_stream else "Suggest 2-3 relevant responses or questions based on user's background"}
3. {"Provide meeting assistance based on combined understanding" if has_dual_stream else "Identify any action items or decisions needed"}
4. Consider topic guidance and relevant documents for conversation direction
5. Reference user's document knowledge when applicable

Response Style: {self.assistant_config.response_style if self.assistant_config else "professional"}
            """,
            "coding": f"""
CODING CONTEXT {"(Dual Audio Stream)" if has_dual_stream else ""}:
User Profile: {{profile}}
{"Prioritized Content: " + prioritized_content if has_dual_stream else "Recent Audio: " + str(transcript)}
Active Window: {{screen_context}}
Clipboard: {{clipboard}}
Topic Guidance: {{topic_guidance}}
Document Context: {{document_context}}

{"DUAL STREAM ANALYSIS - System audio prioritized for learning content:" if has_dual_stream else "Provide coding assistance based on user's skills:"}
1. {"Analyze system audio for tutorial/educational content being consumed" if has_dual_stream else "Analyze current context and user's experience level"}
2. {"Use user voice to understand questions or confusion points" if has_dual_stream else "Suggest code improvements or solutions"}
3. {"Provide coding guidance that bridges tutorial content with user's questions" if has_dual_stream else "Recommend next steps or debugging approaches"}
4. Use knowledge of user's background and document knowledge in recommendations
5. Reference relevant code examples from user's documents

Response Style: {self.assistant_config.response_style if self.assistant_config else "professional"}
            """,
            "general": f"""
GENERAL CONTEXT {"(Dual Audio Stream)" if has_dual_stream else ""}:
User Profile: {{profile}}
{"Prioritized Content: " + prioritized_content if has_dual_stream else "Recent Audio: " + str(transcript)}
Screen Context: {{screen_context}}
Clipboard: {{clipboard}}
Topic Guidance: {{topic_guidance}}
Document Context: {{document_context}}

{"DUAL STREAM ANALYSIS - System audio prioritized:" if has_dual_stream else "Provide helpful assistance:"}
1. {"Primary focus: System audio content (what user is listening to/watching)" if has_dual_stream else "Analyze the current situation considering user's background"}
2. {"Secondary focus: User voice for questions, reactions, or clarifications" if has_dual_stream else "Suggest 2-3 practical next steps relevant to user's skills"}
3. {"Provide assistance that connects external content with user's needs" if has_dual_stream else "Offer relevant tips or information based on user's experience"}
4. Consider topic guidance and relevant documents for additional context
5. Reference user's document knowledge when applicable

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
            topic_guidance=topic_guidance or "No specific topic guidance",
            document_context=document_context or "No relevant documents found"
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
    
    def update_config(self, new_config: Optional[AIProviderConfig]):
        """Update AI configuration"""
        self.config = new_config
        self.ai_available = new_config is not None and new_config.type not in [None, "", "none"]

        if self.ai_available:
            self._setup_client()
            self._initialize_connection_pool()
        else:
            print("[AI] AI provider disabled - switched to transcription-only mode")
    
    async def _get_relevant_documents(self, transcript: List[str], screen_context: str,
                                     clipboard_content: str, context_type: str) -> str:
        """Get relevant documents from the document store"""
        if not self.document_store:
            return "No document knowledge base available"

        try:
            # Create a query from the current context
            query_parts = []

            # Add transcript content
            if transcript:
                # Combine recent transcript entries
                transcript_text = " ".join(transcript[-3:])  # Last 3 entries
                query_parts.append(transcript_text[:200])  # Limit length

            # Add screen context
            if screen_context:
                query_parts.append(screen_context[:100])

            # Add clipboard content
            if clipboard_content:
                query_parts.append(clipboard_content[:100])

            query = " ".join(query_parts)

            if not query.strip():
                return "No searchable context available"

            # Search for relevant documents
            max_chunks = self.config_manager.get_document_config().max_context_chunks if self.config_manager else 3
            results = await self.document_store.query(query, top_k=max_chunks)

            if not results:
                return "No relevant documents found"

            # Format results for context
            context_parts = []
            for chunk, similarity in results:
                # Include source information
                source_info = f"From {chunk.metadata.get('file_name', 'document')}"
                if chunk.metadata.get('document_id'):
                    source_info += f" (chunk {chunk.chunk_index + 1}/{chunk.total_chunks})"

                context_parts.append(f"{source_info}:\n{chunk.content[:500]}...")

            return "\n\n".join(context_parts)

        except Exception as e:
            print(f"Error retrieving documents: {e}")
            return "Error accessing document knowledge base"

    async def add_document_async(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a document asynchronously using the task queue"""
        if not self.document_store:
            raise ValueError("Document store not available")

        try:
            from utils.performance_manager import performance_manager

            # Add file to document store (synchronous metadata operation)
            doc_id = await self.document_store.add_file(file_path, metadata)

            # Queue background processing
            await performance_manager.task_queue.submit(
                priority=2,  # Medium priority
                coro_or_func=self._process_document_background,
                doc_id=doc_id
            )

            return doc_id
        except Exception as e:
            print(f"Failed to queue document processing: {e}")
            raise

    async def _process_document_background(self, doc_id: str) -> None:
        """Background task to process a document"""
        try:
            if self.document_store:
                success = await self.document_store.process_document(doc_id)
                status = "completed" if success else "failed"
                print(f"[DOCS] Background processing {status} for document {doc_id}")
        except Exception as e:
            print(f"[DOCS] Background processing failed for document {doc_id}: {e}")

    async def delete_document_async(self, doc_id: str) -> bool:
        """Delete a document asynchronously"""
        if not self.document_store:
            return False

        try:
            return await self.document_store.delete_document(doc_id)
        except Exception as e:
            print(f"Failed to delete document {doc_id}: {e}")
            return False

    def get_document_store_stats(self) -> Optional[Dict[str, Any]]:
        """Get document store statistics"""
        if self.document_store:
            return asyncio.run(self.document_store.get_stats())
        return None

    def list_documents(self) -> List[Dict[str, Any]]:
        """List all documents with their metadata"""
        if not self.document_store:
            return []

        documents = self.document_store.list_documents()
        return [doc.__dict__ for doc in documents]

    def update_assistant_config(self, new_assistant_config: AssistantConfig):
        """Update assistant configuration"""
        self.assistant_config = new_assistant_config
        print(f"[CONFIG] Updated assistant config: {new_assistant_config.response_style} style, {new_assistant_config.verbosity} verbosity") 