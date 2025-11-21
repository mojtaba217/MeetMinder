import re
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass
import yaml

@dataclass
class UserProfile:
    name: str = ""
    title: str = ""
    education: List[str] = None
    skills: List[str] = None
    experience: List[str] = None
    projects: List[str] = None
    summary: str = ""
    
    def __post_init__(self):
        if self.education is None:
            self.education = []
        if self.skills is None:
            self.skills = []
        if self.experience is None:
            self.experience = []
        if self.projects is None:
            self.projects = []

class UserProfileManager:
    def __init__(self, config, document_store=None):
        self.config = config
        self.profile = UserProfile()
        self.resume_path = Path(config.get('user_profile.resume_path', 'data/resume.md'))
        self.auto_reload = config.get('user_profile.auto_reload', True)
        self.last_modified = None
        self.document_store = document_store  # Optional document store for enhanced profile

        if config.get('user_profile.enabled', True):
            self.load_profile()
    
    def load_profile(self) -> bool:
        """Load and parse user profile from resume file"""
        try:
            if not self.resume_path.exists():
                self._create_sample_resume()
                return False
                
            # Check if file was modified
            current_modified = self.resume_path.stat().st_mtime
            if self.last_modified and current_modified == self.last_modified:
                return True
                
            with open(self.resume_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            self.profile = self._parse_resume(content)
            self.last_modified = current_modified
            
            print(f"[PROFILE] Loaded user profile: {self.profile.name}")
            return True
            
        except Exception as e:
            print(f"Error loading user profile: {e}")
            return False
    
    def _parse_resume(self, content: str) -> UserProfile:
        """Parse resume content into structured profile"""
        profile = UserProfile()
        
        # Extract name from first heading or line
        name_match = re.search(r'^#\s*(.+)$|^(.+)$', content, re.MULTILINE)
        if name_match:
            profile.name = (name_match.group(1) or name_match.group(2)).strip()
        
        # Extract sections using headers
        sections = self._extract_sections(content)
        
        # Parse education
        education_section = sections.get('education', '')
        profile.education = self._extract_bullet_points(education_section)
        
        # Parse skills
        skills_section = sections.get('skills', '')
        profile.skills = self._extract_skills(skills_section)
        
        # Parse experience
        experience_section = sections.get('experience', '')
        profile.experience = self._extract_experience(experience_section)
        
        # Parse projects
        projects_section = sections.get('projects', '')
        profile.projects = self._extract_bullet_points(projects_section)
        
        # Generate summary
        profile.summary = self._generate_summary(profile)
        
        return profile
    
    def _extract_sections(self, content: str) -> Dict[str, str]:
        """Extract sections based on markdown headers"""
        sections = {}
        current_section = None
        current_content = []
        
        for line in content.split('\n'):
            # Check for headers
            header_match = re.match(r'^#{1,3}\s*(.+)$', line)
            if header_match:
                # Save previous section
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                
                # Start new section
                current_section = header_match.group(1).lower().strip()
                current_content = []
            else:
                if current_section:
                    current_content.append(line)
        
        # Save last section
        if current_section:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _extract_bullet_points(self, text: str) -> List[str]:
        """Extract bullet points from text"""
        bullets = []
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith(('•', '-', '*', '+')):
                bullet = re.sub(r'^[•\-\*\+]\s*', '', line).strip()
                if bullet:
                    bullets.append(bullet)
        return bullets
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from text with various formats"""
        skills = []
        
        # Try bullet points first
        bullets = self._extract_bullet_points(text)
        if bullets:
            # Split comma-separated items in bullets
            for bullet in bullets:
                skills.extend([s.strip() for s in bullet.split(',') if s.strip()])
        else:
            # Try comma-separated on single line
            for line in text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    skills.extend([s.strip() for s in line.split(',') if s.strip()])
        
        return skills[:10]  # Limit to top 10 skills
    
    def _extract_experience(self, text: str) -> List[str]:
        """Extract work experience entries"""
        experience = []
        
        # Look for job title + company patterns
        job_pattern = r'(.+?)\s*(?:at|@)\s*(.+?)(?:\s*\|\s*(.+?))?(?:\n|$)'
        matches = re.findall(job_pattern, text, re.IGNORECASE)
        
        for match in matches:
            title, company, duration = match
            if title and company:
                exp_entry = f"{title.strip()} at {company.strip()}"
                if duration.strip():
                    exp_entry += f" ({duration.strip()})"
                experience.append(exp_entry)
        
        # Fallback to bullet points
        if not experience:
            experience = self._extract_bullet_points(text)
        
        return experience[:5]  # Limit to 5 most recent
    
    def _generate_summary(self, profile: UserProfile) -> str:
        """Generate a concise profile summary"""
        summary_parts = []
        
        # Add education
        if profile.education:
            edu = profile.education[0]  # Most recent
            summary_parts.append(f"• {edu}")
        
        # Add top skills
        if profile.skills:
            top_skills = profile.skills[:5]
            summary_parts.append(f"• Skills: {', '.join(top_skills)}")
        
        # Add recent experience
        if profile.experience:
            recent_exp = profile.experience[0]  # Most recent
            summary_parts.append(f"• {recent_exp}")
        
        return '\n'.join(summary_parts)
    
    def get_profile_summary(self) -> str:
        """Get formatted profile summary for AI prompts"""
        if self.auto_reload:
            self.load_profile()

        if not self.profile.summary:
            return "• No profile information available"

        return self.profile.summary

    async def get_profile_summary_async(self) -> str:
        """Get profile summary with optional document enhancement"""
        base_summary = self.get_profile_summary()

        # If document store is available, enhance with document-based context
        if self.document_store:
            try:
                # Query for resume-related documents
                resume_docs = await self.document_store.query(
                    "resume CV curriculum vitae profile background experience skills",
                    top_k=2
                )

                if resume_docs:
                    doc_contexts = []
                    for chunk, similarity in resume_docs:
                        if similarity > 0.7:  # Only include highly relevant chunks
                            doc_contexts.append(f"From documents: {chunk.content[:300]}...")

                    if doc_contexts:
                        base_summary += "\n\nAdditional context from uploaded documents:\n" + "\n".join(doc_contexts)

            except Exception as e:
                print(f"Error getting document-enhanced profile: {e}")

        return base_summary
    
    def _create_sample_resume(self):
        """Create a sample resume file"""
        sample_content = """# John Doe

## Education
• PhD in Computer Science (NLP) - Stanford University
• MS in Data Science - MIT

## Skills
Python, Machine Learning, Data Engineering, NLP, TensorFlow, PyTorch, SQL, AWS, Docker

## Experience
• Senior ML Engineer at Google - Speech & Vision Teams (2019-2024)
• Data Scientist at Microsoft - Azure AI (2017-2019)
• Software Engineer at Startup - ML Platform (2015-2017)

## Projects
• Built real-time speech recognition system serving 10M+ users
• Developed computer vision pipeline for autonomous vehicles
• Created NLP models for sentiment analysis and text classification
"""
        
        # Create directory if it doesn't exist
        self.resume_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.resume_path, 'w', encoding='utf-8') as file:
            file.write(sample_content)
        
        print(f"[SAMPLE] Created sample resume at {self.resume_path}") 