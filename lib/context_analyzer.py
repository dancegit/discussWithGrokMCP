"""
Context Analyzer - Intelligent context detection with NLP enhancement.
"""

import os
import re
import asyncio
import aiofiles
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging
import json
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class ContextItem:
    """Represents a piece of context."""
    path: str
    content: str
    relevance_score: float
    token_estimate: int
    type: str  # file, snippet, documentation, etc.
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "relevance_score": self.relevance_score,
            "token_estimate": self.token_estimate,
            "type": self.type,
            "metadata": self.metadata,
            "content_preview": self.content[:200] + "..." if len(self.content) > 200 else self.content
        }


class ContextAnalyzer:
    """Analyzes questions and gathers intelligent context."""
    
    def __init__(self, project_root: Optional[Path] = None, token_budget: int = 10000):
        """Initialize context analyzer.
        
        Args:
            project_root: Root directory of the project
            token_budget: Maximum tokens for context
        """
        self.project_root = project_root or Path.cwd()
        self.token_budget = token_budget
        
        # Question type patterns
        self.question_patterns = {
            "implementation": [
                r"how (do|can|should) (i|we)",
                r"implement",
                r"create",
                r"build",
                r"add",
                r"develop"
            ],
            "debugging": [
                r"error",
                r"bug",
                r"fix",
                r"issue",
                r"problem",
                r"not working",
                r"fails?",
                r"crash",
                r"exception"
            ],
            "optimization": [
                r"optimi[zs]e",
                r"improve",
                r"faster",
                r"better",
                r"performance",
                r"efficient",
                r"reduce",
                r"speed up"
            ],
            "explanation": [
                r"what (is|are|does)",
                r"explain",
                r"understand",
                r"why",
                r"how does",
                r"describe"
            ],
            "testing": [
                r"test",
                r"verify",
                r"validate",
                r"check",
                r"assert",
                r"mock"
            ]
        }
        
        # File type associations
        self.file_associations = {
            "python": [".py", ".pyi"],
            "javascript": [".js", ".jsx", ".ts", ".tsx"],
            "config": [".json", ".yaml", ".yml", ".toml", ".ini"],
            "documentation": [".md", ".rst", ".txt"],
            "web": [".html", ".css", ".scss"]
        }
    
    async def analyze_question(self, question: str) -> Dict[str, Any]:
        """Analyze a question to determine type and extract key information.
        
        Args:
            question: User's question
            
        Returns:
            Analysis results including type, keywords, entities
        """
        analysis = {
            "question": question,
            "type": self._detect_question_type(question),
            "keywords": self._extract_keywords(question),
            "entities": self._extract_entities(question),
            "file_references": self._extract_file_references(question),
            "requires_code": self._requires_code_context(question)
        }
        
        logger.debug(f"Question analysis: {analysis}")
        return analysis
    
    def _detect_question_type(self, question: str) -> str:
        """Detect the type of question.
        
        Args:
            question: User's question
            
        Returns:
            Question type
        """
        question_lower = question.lower()
        scores = {}
        
        for q_type, patterns in self.question_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    score += 1
            scores[q_type] = score
        
        # Return type with highest score, default to "general"
        if scores:
            return max(scores, key=scores.get)
        return "general"
    
    def _extract_keywords(self, question: str) -> List[str]:
        """Extract important keywords from the question.
        
        Args:
            question: User's question
            
        Returns:
            List of keywords
        """
        # Remove common words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
            "be", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "must", "can", "shall", "need"
        }
        
        # Tokenize and filter
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', question.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Count frequency and return top keywords
        word_freq = Counter(keywords)
        return [word for word, _ in word_freq.most_common(10)]
    
    def _extract_entities(self, question: str) -> Dict[str, List[str]]:
        """Extract entities like function names, classes, files.
        
        Args:
            question: User's question
            
        Returns:
            Dictionary of entity types and values
        """
        entities = {
            "functions": [],
            "classes": [],
            "files": [],
            "modules": []
        }
        
        # Function/method patterns (camelCase or snake_case followed by parentheses)
        func_pattern = r'\b([a-z_][a-zA-Z0-9_]*|[a-z][a-zA-Z0-9]*)\s*\('
        entities["functions"] = re.findall(func_pattern, question)
        
        # Class patterns (PascalCase)
        class_pattern = r'\b([A-Z][a-zA-Z0-9]+)\b'
        entities["classes"] = re.findall(class_pattern, question)
        
        # File patterns
        file_pattern = r'([a-zA-Z0-9_\-]+\.[a-zA-Z0-9]+)'
        entities["files"] = re.findall(file_pattern, question)
        
        # Module/package patterns (dot notation)
        module_pattern = r'\b([a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)+)\b'
        entities["modules"] = re.findall(module_pattern, question)
        
        return entities
    
    def _extract_file_references(self, question: str) -> List[str]:
        """Extract file paths or names mentioned in the question.
        
        Args:
            question: User's question
            
        Returns:
            List of file references
        """
        files = []
        
        # Direct file paths
        path_pattern = r'(?:[.\/\\])?(?:[a-zA-Z0-9_\-]+[\/\\])*[a-zA-Z0-9_\-]+\.[a-zA-Z0-9]+'
        files.extend(re.findall(path_pattern, question))
        
        # File names without extension but with common prefixes
        name_pattern = r'\b(test_|spec_|config|settings|main|index|app)\w*\b'
        potential_files = re.findall(name_pattern, question, re.IGNORECASE)
        files.extend(potential_files)
        
        return list(set(files))
    
    def _requires_code_context(self, question: str) -> bool:
        """Determine if the question requires code context.
        
        Args:
            question: User's question
            
        Returns:
            True if code context is likely needed
        """
        code_indicators = [
            "function", "method", "class", "variable", "parameter",
            "implement", "code", "syntax", "error", "bug", "line",
            "import", "module", "package", "library", "api"
        ]
        
        question_lower = question.lower()
        return any(indicator in question_lower for indicator in code_indicators)
    
    async def gather_context(
        self,
        analysis: Dict[str, Any],
        include_files: Optional[List[str]] = None
    ) -> List[ContextItem]:
        """Gather relevant context based on analysis.
        
        Args:
            analysis: Question analysis results
            include_files: Specific files to include
            
        Returns:
            List of context items within token budget
        """
        context_items = []
        
        # 1. Add specifically requested files
        if include_files:
            for file_path in include_files:
                item = await self._load_file_context(file_path)
                if item:
                    context_items.append(item)
        
        # 2. Find files based on entities
        entities = analysis.get("entities", {})
        for file_ref in entities.get("files", []):
            files = await self._find_files_by_name(file_ref)
            for file_path in files[:3]:  # Limit to top 3 matches
                item = await self._load_file_context(file_path)
                if item:
                    context_items.append(item)
        
        # 3. Find files based on keywords
        keywords = analysis.get("keywords", [])
        relevant_files = await self._find_relevant_files(keywords, analysis.get("type", "general"))
        for file_path in relevant_files[:5]:  # Top 5 relevant files
            item = await self._load_file_context(file_path)
            if item:
                context_items.append(item)
        
        # 4. Add configuration files if needed
        if analysis.get("type") in ["implementation", "debugging"]:
            config_files = await self._find_config_files()
            for file_path in config_files[:2]:
                item = await self._load_file_context(file_path)
                if item:
                    context_items.append(item)
        
        # 5. Score and prioritize context items
        scored_items = self._score_context_items(context_items, analysis)
        
        # 6. Fit within token budget
        final_context = self._fit_token_budget(scored_items)
        
        return final_context
    
    async def _load_file_context(self, file_path: str) -> Optional[ContextItem]:
        """Load a file as a context item.
        
        Args:
            file_path: Path to the file
            
        Returns:
            ContextItem or None if file cannot be loaded
        """
        full_path = self.project_root / file_path
        
        if not full_path.exists() or not full_path.is_file():
            return None
        
        try:
            async with aiofiles.open(full_path, 'r') as f:
                content = await f.read()
            
            # Skip very large files
            if len(content) > 50000:
                content = content[:50000] + "\n... (truncated)"
            
            return ContextItem(
                path=str(file_path),
                content=content,
                relevance_score=0.5,  # Default score, will be updated
                token_estimate=len(content) // 4,
                type="file",
                metadata={
                    "size": len(content),
                    "extension": full_path.suffix
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to load file {file_path}: {e}")
            return None
    
    async def _find_files_by_name(self, name_pattern: str) -> List[str]:
        """Find files matching a name pattern.
        
        Args:
            name_pattern: File name or pattern to search
            
        Returns:
            List of file paths
        """
        matches = []
        
        # Walk through project directory
        for root, dirs, files in os.walk(self.project_root):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv']]
            
            for file in files:
                if name_pattern.lower() in file.lower():
                    rel_path = Path(root) / file
                    matches.append(str(rel_path.relative_to(self.project_root)))
        
        return matches[:10]  # Limit results
    
    async def _find_relevant_files(self, keywords: List[str], question_type: str) -> List[str]:
        """Find files relevant to keywords and question type.
        
        Args:
            keywords: List of keywords
            question_type: Type of question
            
        Returns:
            List of relevant file paths
        """
        relevant_files = []
        file_scores = {}
        
        # Determine preferred file types based on question type
        if question_type == "testing":
            preferred_patterns = ["test_", "_test", "spec_", "_spec"]
        elif question_type == "implementation":
            preferred_patterns = ["lib/", "src/", "core/"]
        elif question_type == "configuration":
            preferred_patterns = ["config", "settings", ".env", ".json", ".yaml"]
        else:
            preferred_patterns = []
        
        # Walk through project
        for root, dirs, files in os.walk(self.project_root):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv']]
            
            for file in files:
                # Skip non-text files
                if not any(file.endswith(ext) for ext in ['.py', '.js', '.ts', '.json', '.yaml', '.md', '.txt']):
                    continue
                
                rel_path = Path(root) / file
                file_path = str(rel_path.relative_to(self.project_root))
                
                # Calculate relevance score
                score = 0
                
                # Check for keyword matches in filename
                for keyword in keywords:
                    if keyword.lower() in file.lower():
                        score += 2
                    if keyword.lower() in file_path.lower():
                        score += 1
                
                # Boost for preferred patterns
                for pattern in preferred_patterns:
                    if pattern in file_path.lower():
                        score += 3
                
                if score > 0:
                    file_scores[file_path] = score
        
        # Sort by score and return top files
        sorted_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)
        return [f[0] for f in sorted_files[:10]]
    
    async def _find_config_files(self) -> List[str]:
        """Find configuration files in the project.
        
        Returns:
            List of configuration file paths
        """
        config_files = []
        config_patterns = [
            "pyproject.toml", "package.json", "requirements.txt",
            ".env", ".env.example", "config.json", "config.yaml",
            "settings.py", "config.py", "setup.py"
        ]
        
        for pattern in config_patterns:
            file_path = self.project_root / pattern
            if file_path.exists():
                config_files.append(pattern)
        
        return config_files
    
    def _score_context_items(
        self,
        items: List[ContextItem],
        analysis: Dict[str, Any]
    ) -> List[ContextItem]:
        """Score and sort context items by relevance.
        
        Args:
            items: List of context items
            analysis: Question analysis
            
        Returns:
            Sorted list of context items
        """
        keywords = analysis.get("keywords", [])
        entities = analysis.get("entities", {})
        
        for item in items:
            score = item.relevance_score
            
            # Score based on keyword matches in content
            content_lower = item.content.lower()
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    # Count occurrences (up to 5)
                    count = min(content_lower.count(keyword.lower()), 5)
                    score += count * 0.1
            
            # Score based on entity matches
            for entity_list in entities.values():
                for entity in entity_list:
                    if entity in item.content:
                        score += 0.3
            
            # Penalty for very large files
            if item.token_estimate > 2000:
                score *= 0.7
            
            item.relevance_score = min(score, 1.0)
        
        # Sort by relevance score
        return sorted(items, key=lambda x: x.relevance_score, reverse=True)
    
    def _fit_token_budget(self, items: List[ContextItem]) -> List[ContextItem]:
        """Fit context items within token budget.
        
        Args:
            items: Sorted list of context items
            
        Returns:
            List of items that fit within budget
        """
        selected = []
        total_tokens = 0
        
        for item in items:
            if total_tokens + item.token_estimate <= self.token_budget:
                selected.append(item)
                total_tokens += item.token_estimate
            else:
                # Try to add a truncated version
                remaining_tokens = self.token_budget - total_tokens
                if remaining_tokens > 500:  # Only if meaningful content can be added
                    # Truncate content to fit
                    truncated_content = item.content[:remaining_tokens * 4]
                    item.content = truncated_content + "\n... (truncated to fit token budget)"
                    item.token_estimate = remaining_tokens
                    selected.append(item)
                break
        
        logger.info(f"Selected {len(selected)} context items, total tokens: {total_tokens}")
        return selected
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        # Rough estimate: 1 token per 4 characters
        return len(text) // 4