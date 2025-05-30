import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class TopicNode:
    """Represents a topic in the knowledge graph"""
    name: str
    category: str
    subcategory: str
    keywords: List[str]
    related_topics: List[str]
    suggestions: List[str]
    depth_level: int = 0

@dataclass
class TopicPath:
    """Represents the current topic path in conversation"""
    category: str
    subcategory: str
    specific_topic: str
    current_focus: str
    confidence: float
    timestamp: float

class LiveTopicAnalyzer:
    """Real-time topic analysis using LLM and knowledge graph"""
    
    def __init__(self, ai_helper, config_manager):
        self.ai_helper = ai_helper
        self.config_manager = config_manager
        self.knowledge_graph = {}
        self.current_path = None
        self.conversation_history = []
        self.topic_transitions = []
        self.load_knowledge_graph()
    
    def load_knowledge_graph(self):
        """Load the predefined knowledge graph"""
        graph_path = Path("data/topic_graph.json")
        
        if graph_path.exists():
            try:
                with open(graph_path, 'r', encoding='utf-8') as f:
                    graph_data = json.load(f)
                    self.knowledge_graph = {
                        topic['name']: TopicNode(**topic) 
                        for topic in graph_data.get('topics', [])
                    }
                print(f"✅ Loaded {len(self.knowledge_graph)} topics from knowledge graph")
            except Exception as e:
                print(f"❌ Error loading knowledge graph: {e}")
                self._create_default_graph()
        else:
            self._create_default_graph()
    
    def _create_default_graph(self):
        """Create a default knowledge graph"""
        default_topics = [
            {
                "name": "Machine Learning",
                "category": "AI",
                "subcategory": "Machine Learning",
                "keywords": ["ml", "model", "training", "algorithm", "neural network"],
                "related_topics": ["Deep Learning", "Data Science", "Statistics"],
                "suggestions": [
                    "Consider discussing model evaluation metrics",
                    "Explore different algorithm types for this use case",
                    "Discuss data preprocessing requirements"
                ],
                "depth_level": 1
            },
            {
                "name": "Model Evaluation",
                "category": "AI",
                "subcategory": "Machine Learning",
                "keywords": ["accuracy", "precision", "recall", "f1", "validation", "overfitting"],
                "related_topics": ["Cross Validation", "Hyperparameter Tuning", "Bias-Variance"],
                "suggestions": [
                    "Emphasize use of validation sets and cross-validation",
                    "Discuss appropriate metrics for the problem type",
                    "Consider ensemble methods for better performance"
                ],
                "depth_level": 2
            },
            {
                "name": "Software Development",
                "category": "Technology",
                "subcategory": "Programming",
                "keywords": ["code", "programming", "development", "software", "application"],
                "related_topics": ["Code Review", "Testing", "Architecture"],
                "suggestions": [
                    "Follow best practices and coding standards",
                    "Implement proper error handling",
                    "Consider scalability and maintainability"
                ],
                "depth_level": 1
            },
            {
                "name": "Code Review",
                "category": "Technology",
                "subcategory": "Programming",
                "keywords": ["review", "pull request", "feedback", "quality", "standards"],
                "related_topics": ["Testing", "Documentation", "Version Control"],
                "suggestions": [
                    "Focus on code readability and maintainability",
                    "Check for security vulnerabilities",
                    "Ensure proper test coverage"
                ],
                "depth_level": 2
            }
        ]
        
        self.knowledge_graph = {
            topic['name']: TopicNode(**topic) 
            for topic in default_topics
        }
        
        # Save default graph
        self._save_knowledge_graph()
        print(f"✅ Created default knowledge graph with {len(self.knowledge_graph)} topics")
    
    def _save_knowledge_graph(self):
        """Save the knowledge graph to file"""
        try:
            graph_path = Path("data/topic_graph.json")
            graph_path.parent.mkdir(exist_ok=True)
            
            graph_data = {
                'topics': [
                    {
                        'name': topic.name,
                        'category': topic.category,
                        'subcategory': topic.subcategory,
                        'keywords': topic.keywords,
                        'related_topics': topic.related_topics,
                        'suggestions': topic.suggestions,
                        'depth_level': topic.depth_level
                    }
                    for topic in self.knowledge_graph.values()
                ]
            }
            
            with open(graph_path, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"❌ Error saving knowledge graph: {e}")
    
    async def analyze_conversation_flow(self, transcript: List[str], context: str = "") -> Dict[str, Any]:
        """Analyze conversation flow and provide topic guidance"""
        if not transcript:
            return self._get_empty_analysis()
        
        # Combine recent transcript
        recent_text = " ".join(transcript[-5:])  # Last 5 segments
        self.conversation_history.append({
            'text': recent_text,
            'timestamp': time.time(),
            'context': context
        })
        
        # Keep only recent history
        cutoff_time = time.time() - 300  # 5 minutes
        self.conversation_history = [
            h for h in self.conversation_history 
            if h['timestamp'] > cutoff_time
        ]
        
        # Analyze topic path
        topic_path = await self._identify_topic_path(recent_text, context)
        
        if topic_path:
            self.current_path = topic_path
            self.topic_transitions.append(topic_path)
        
        # Generate guidance
        guidance = await self._generate_topic_guidance(topic_path, recent_text)
        
        return {
            'current_path': topic_path,
            'guidance': guidance,
            'related_topics': self._get_related_topics(topic_path),
            'conversation_flow': self._analyze_flow_pattern(),
            'new_topic_detected': self._is_new_topic(topic_path)
        }
    
    async def _identify_topic_path(self, text: str, context: str) -> Optional[TopicPath]:
        """Use LLM to identify the current topic path"""
        try:
            # First, try to match against known topics
            matched_topics = self._match_known_topics(text)
            
            if matched_topics:
                best_match = matched_topics[0]
                topic_node = self.knowledge_graph[best_match]
                
                return TopicPath(
                    category=topic_node.category,
                    subcategory=topic_node.subcategory,
                    specific_topic=topic_node.name,
                    current_focus=await self._extract_current_focus(text, topic_node),
                    confidence=0.8,
                    timestamp=time.time()
                )
            
            # If no match, use LLM to analyze
            return await self._llm_topic_analysis(text, context)
            
        except Exception as e:
            print(f"❌ Error identifying topic path: {e}")
            return None
    
    def _match_known_topics(self, text: str) -> List[str]:
        """Match text against known topics using keywords"""
        text_lower = text.lower()
        matches = []
        
        for topic_name, topic_node in self.knowledge_graph.items():
            score = 0
            for keyword in topic_node.keywords:
                if keyword.lower() in text_lower:
                    score += 1
            
            if score > 0:
                matches.append((topic_name, score))
        
        # Sort by score and return topic names
        matches.sort(key=lambda x: x[1], reverse=True)
        return [match[0] for match in matches[:3]]
    
    async def _llm_topic_analysis(self, text: str, context: str) -> Optional[TopicPath]:
        """Use LLM to analyze topic when no known match is found"""
        try:
            prompt = f"""
Analyze this conversation segment and identify the topic structure:

Text: "{text}"
Context: "{context}"

Known topic categories: {list(set(t.category for t in self.knowledge_graph.values()))}

Provide the topic path in this format:
Category → Subcategory → Specific Topic → Current Focus

If this is a new topic not in our knowledge graph, suggest where it fits.
Be specific about the current focus within the topic.
"""
            
            # Use the AI helper to analyze
            response_chunks = []
            async for chunk in self.ai_helper.analyze_context_stream(
                transcript=[text],
                screen_context=context,
                clipboard_content="",
                context_type="topic_analysis"
            ):
                response_chunks.append(chunk)
            
            response = "".join(response_chunks)
            
            # Parse the response to extract topic path
            return self._parse_llm_topic_response(response)
            
        except Exception as e:
            print(f"❌ Error in LLM topic analysis: {e}")
            return None
    
    def _parse_llm_topic_response(self, response: str) -> Optional[TopicPath]:
        """Parse LLM response to extract topic path"""
        try:
            # Look for the topic path pattern
            lines = response.split('\n')
            for line in lines:
                if '→' in line:
                    parts = [part.strip() for part in line.split('→')]
                    if len(parts) >= 4:
                        return TopicPath(
                            category=parts[0],
                            subcategory=parts[1],
                            specific_topic=parts[2],
                            current_focus=parts[3],
                            confidence=0.6,  # Lower confidence for LLM-generated
                            timestamp=time.time()
                        )
            
            return None
            
        except Exception as e:
            print(f"❌ Error parsing LLM topic response: {e}")
            return None
    
    async def _extract_current_focus(self, text: str, topic_node: TopicNode) -> str:
        """Extract the current focus within a known topic"""
        try:
            # Use a simple approach first - look for specific keywords
            text_lower = text.lower()
            
            # Check for specific focus areas based on topic
            if "evaluation" in text_lower or "metrics" in text_lower:
                return "Evaluation Metrics"
            elif "training" in text_lower or "learning" in text_lower:
                return "Model Training"
            elif "data" in text_lower:
                return "Data Processing"
            elif "testing" in text_lower or "test" in text_lower:
                return "Testing"
            elif "review" in text_lower:
                return "Code Review"
            else:
                return "General Discussion"
                
        except Exception as e:
            print(f"❌ Error extracting current focus: {e}")
            return "Unknown Focus"
    
    async def _generate_topic_guidance(self, topic_path: Optional[TopicPath], text: str) -> str:
        """Generate contextual guidance based on topic path"""
        if not topic_path:
            return "Continue the discussion - no specific topic guidance available."
        
        # Check if we have specific guidance for this topic
        if topic_path.specific_topic in self.knowledge_graph:
            topic_node = self.knowledge_graph[topic_path.specific_topic]
            suggestions = topic_node.suggestions
            
            if suggestions:
                return f"💡 {suggestions[0]}"
        
        # Generate dynamic guidance based on topic path
        guidance_templates = {
            "AI": "Consider the practical applications and limitations of this approach.",
            "Technology": "Think about scalability, maintainability, and best practices.",
            "Business": "Focus on ROI, stakeholder impact, and strategic alignment.",
            "Science": "Examine the methodology, evidence, and reproducibility."
        }
        
        category_guidance = guidance_templates.get(
            topic_path.category, 
            "Explore the implications and next steps for this topic."
        )
        
        return f"💡 {category_guidance}"
    
    def _get_related_topics(self, topic_path: Optional[TopicPath]) -> List[str]:
        """Get related topics for the current path"""
        if not topic_path or topic_path.specific_topic not in self.knowledge_graph:
            return []
        
        topic_node = self.knowledge_graph[topic_path.specific_topic]
        return topic_node.related_topics[:3]  # Return top 3 related topics
    
    def _analyze_flow_pattern(self) -> str:
        """Analyze the conversation flow pattern"""
        if len(self.topic_transitions) < 2:
            return "Starting conversation"
        
        recent_transitions = self.topic_transitions[-3:]
        
        # Check for topic jumping
        categories = [t.category for t in recent_transitions]
        if len(set(categories)) > 2:
            return "Topic jumping - consider focusing on one area"
        
        # Check for deepening discussion
        if len(recent_transitions) >= 2:
            if recent_transitions[-1].specific_topic == recent_transitions[-2].specific_topic:
                return "Deepening discussion - good focus"
        
        return "Natural topic progression"
    
    def _is_new_topic(self, topic_path: Optional[TopicPath]) -> bool:
        """Check if this is a new topic not in our knowledge graph"""
        if not topic_path:
            return False
        
        return topic_path.specific_topic not in self.knowledge_graph
    
    def _get_empty_analysis(self) -> Dict[str, Any]:
        """Return empty analysis when no transcript is available"""
        return {
            'current_path': None,
            'guidance': "Start speaking to get topic guidance",
            'related_topics': [],
            'conversation_flow': "Waiting for input",
            'new_topic_detected': False
        }
    
    def get_current_topic_display(self) -> str:
        """Get formatted display of current topic path"""
        if not self.current_path:
            return "No active topic"
        
        path_str = f"{self.current_path.category} → {self.current_path.subcategory} → {self.current_path.specific_topic}"
        
        if self.current_path.current_focus != "General Discussion":
            path_str += f" → {self.current_path.current_focus}"
        
        return path_str
    
    async def add_new_topic(self, topic_name: str, category: str, subcategory: str, keywords: List[str]):
        """Add a new topic to the knowledge graph"""
        try:
            new_topic = TopicNode(
                name=topic_name,
                category=category,
                subcategory=subcategory,
                keywords=keywords,
                related_topics=[],
                suggestions=[f"Explore {topic_name} in more detail"],
                depth_level=1
            )
            
            self.knowledge_graph[topic_name] = new_topic
            self._save_knowledge_graph()
            
            print(f"✅ Added new topic: {topic_name}")
            
        except Exception as e:
            print(f"❌ Error adding new topic: {e}") 