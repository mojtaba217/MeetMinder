import re
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class TopicNode:
    name: str
    parent: Optional[str] = None
    children: List[str] = None
    suggestion: str = ""
    
    def __post_init__(self):
        if self.children is None:
            self.children = []

@dataclass
class TopicMatch:
    topic: str
    confidence: float
    suggestion: str = ""
    path: List[str] = None
    
    def __post_init__(self):
        if self.path is None:
            self.path = []

class TopicGraphManager:
    def __init__(self, config):
        self.config = config
        self.graph_path = Path(config.get('topic_graph.graph_path', 'data/topic_graph.txt'))
        self.matching_threshold = config.get('topic_graph.matching_threshold', 0.6)
        self.max_matches = config.get('topic_graph.max_matches', 3)
        self.new_topic_threshold = config.get('topic_graph.new_topic_threshold', 0.3)
        
        self.topics: Dict[str, TopicNode] = {}
        self.topic_keywords: Dict[str, List[str]] = {}
        self.last_modified = None
        
        if config.get('topic_graph.enabled', True):
            self.load_topic_graph()
    
    def load_topic_graph(self) -> bool:
        """Load topic graph from definition file"""
        try:
            if not self.graph_path.exists():
                self._create_sample_graph()
                return False
                
            # Check if file was modified
            current_modified = self.graph_path.stat().st_mtime
            if self.last_modified and current_modified == self.last_modified:
                return True
                
            with open(self.graph_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            self._parse_topic_graph(content)
            self.last_modified = current_modified
            
            print(f"✓ Loaded topic graph with {len(self.topics)} topics")
            return True
            
        except Exception as e:
            print(f"Error loading topic graph: {e}")
            return False
    
    def _parse_topic_graph(self, content: str):
        """Parse topic graph definition"""
        self.topics.clear()
        self.topic_keywords.clear()
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse: Parent -> Child (suggestion: "text")
            match = re.match(r'(.+?)\s*->\s*(.+?)(?:\s*\(suggestion:\s*["\'](.+?)["\']\))?$', line)
            if match:
                parent_name = match.group(1).strip()
                child_name = match.group(2).strip()
                suggestion = match.group(3) or ""
                
                # Create or get parent node
                if parent_name not in self.topics:
                    self.topics[parent_name] = TopicNode(parent_name)
                    self.topic_keywords[parent_name] = self._extract_keywords(parent_name)
                
                # Create or get child node
                if child_name not in self.topics:
                    self.topics[child_name] = TopicNode(child_name, parent=parent_name, suggestion=suggestion)
                    self.topic_keywords[child_name] = self._extract_keywords(child_name)
                else:
                    self.topics[child_name].parent = parent_name
                    if suggestion:
                        self.topics[child_name].suggestion = suggestion
                
                # Add child to parent
                if child_name not in self.topics[parent_name].children:
                    self.topics[parent_name].children.append(child_name)
    
    def _extract_keywords(self, topic_name: str) -> List[str]:
        """Extract keywords from topic name for matching"""
        # Convert to lowercase and split
        words = re.findall(r'\b\w+\b', topic_name.lower())
        
        # Add variations
        keywords = set(words)
        
        # Add stemmed versions (simple stemming)
        for word in words:
            if word.endswith('ing'):
                keywords.add(word[:-3])
            elif word.endswith('s') and len(word) > 3:
                keywords.add(word[:-1])
        
        return list(keywords)
    
    def match_topics(self, transcript_text: str) -> List[TopicMatch]:
        """Match topics against transcript text"""
        if not self.topics:
            return []
        
        text_lower = transcript_text.lower()
        matches = []
        
        for topic_name, keywords in self.topic_keywords.items():
            confidence = self._calculate_confidence(text_lower, keywords)
            
            if confidence >= self.matching_threshold:
                topic_node = self.topics[topic_name]
                matches.append(TopicMatch(
                    topic=topic_name,
                    confidence=confidence,
                    suggestion=topic_node.suggestion,
                    path=self._get_topic_path(topic_name)
                ))
        
        # Sort by confidence and return top matches
        matches.sort(key=lambda x: x.confidence, reverse=True)
        return matches[:self.max_matches]
    
    def _calculate_confidence(self, text: str, keywords: List[str]) -> float:
        """Calculate confidence score for topic matching"""
        if not keywords:
            return 0.0
        
        # Count keyword matches
        matches = 0
        for keyword in keywords:
            if keyword in text:
                matches += 1
        
        # Base confidence
        confidence = matches / len(keywords)
        
        # Boost for exact phrase matches
        topic_name = keywords[0] if keywords else ""
        if topic_name in text:
            confidence += 0.3
        
        return min(confidence, 1.0)
    
    def _get_topic_path(self, topic_name: str) -> List[str]:
        """Get the path from root to topic"""
        path = []
        current = topic_name
        
        while current:
            path.insert(0, current)
            current = self.topics.get(current, TopicNode("")).parent
            
            # Prevent infinite loops
            if len(path) > 5:
                break
        
        return path
    
    def detect_new_topics(self, transcript_text: str) -> List[str]:
        """Detect potential new topics not in graph"""
        if not transcript_text:
            return []
        
        # Extract potential topic phrases
        phrases = self._extract_topic_phrases(transcript_text)
        new_topics = []
        
        for phrase in phrases:
            # Check if this could be a new topic
            best_match_confidence = 0.0
            for keywords in self.topic_keywords.values():
                confidence = self._calculate_confidence(phrase.lower(), keywords)
                best_match_confidence = max(best_match_confidence, confidence)
            
            # If no good match found, might be new topic
            if best_match_confidence < self.new_topic_threshold:
                new_topics.append(phrase)
        
        return new_topics[:3]  # Limit to 3 suggestions
    
    def _extract_topic_phrases(self, text: str) -> List[str]:
        """Extract potential topic phrases from text"""
        phrases = []
        
        # Extract noun phrases (simple version)
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        phrases.extend(words)
        
        # Extract quoted phrases
        quoted = re.findall(r'"([^"]+)"', text)
        phrases.extend(quoted)
        
        # Extract technical terms (words with specific patterns)
        tech_terms = re.findall(r'\b[A-Z]{2,}|\b\w*[A-Z]\w*[A-Z]\w*\b', text)
        phrases.extend(tech_terms)
        
        return [p for p in phrases if len(p) > 3 and len(p) < 30]
    
    def get_topic_suggestions(self, matches: List[TopicMatch]) -> List[str]:
        """Get actionable suggestions based on matched topics"""
        suggestions = []
        
        for match in matches:
            if match.suggestion:
                suggestions.append(f"💡 {match.topic}: {match.suggestion}")
            else:
                # Generate generic suggestion
                path_str = " → ".join(match.path)
                suggestions.append(f"🎯 Consider exploring: {path_str}")
        
        return suggestions
    
    def _create_sample_graph(self):
        """Create a sample topic graph file"""
        sample_content = """# Topic Graph Definition
# Format: Parent -> Child (suggestion: "Optional suggestion text")

Machine Learning -> Supervised Learning (suggestion: "Discuss classification vs regression approaches")
Machine Learning -> Unsupervised Learning (suggestion: "Explore clustering and dimensionality reduction")
Machine Learning -> Error Analysis (suggestion: "Ask how to debug your model's loss spikes")
Machine Learning -> Validation Techniques (suggestion: "Request more robust cross-val strategies")

Data Engineering -> ETL Pipelines (suggestion: "Review data transformation and validation steps")
Data Engineering -> Data Quality (suggestion: "Discuss monitoring and anomaly detection")
Data Engineering -> Scalability (suggestion: "Explore distributed processing solutions")

NLP -> Text Preprocessing (suggestion: "Cover tokenization, normalization, and feature extraction")
NLP -> Language Models (suggestion: "Compare transformer architectures and fine-tuning")
NLP -> Sentiment Analysis (suggestion: "Discuss approach selection and evaluation metrics")

Computer Vision -> Image Classification (suggestion: "Review CNN architectures and transfer learning")
Computer Vision -> Object Detection (suggestion: "Compare YOLO, R-CNN, and newer approaches")

Deep Learning -> Neural Networks (suggestion: "Cover architecture design and optimization")
Deep Learning -> Training Strategies (suggestion: "Discuss learning rates, regularization, and convergence")

Career Development -> Technical Interviews (suggestion: "Practice system design and coding problems")
Career Development -> Skill Building (suggestion: "Identify learning paths and project ideas")
"""
        
        # Create directory if it doesn't exist
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.graph_path, 'w', encoding='utf-8') as file:
            file.write(sample_content)
        
        print(f"✓ Created sample topic graph at {self.graph_path}") 