"""
Baseline Generator - Creates structured baseline documents for complex discussions.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import logging

from .context_analyzer import ContextItem

logger = logging.getLogger(__name__)


@dataclass
class BaselineSection:
    """Represents a section of the baseline document."""
    title: str
    content: str
    priority: int = 1  # 1=highest, 5=lowest
    token_estimate: int = 0
    
    def __post_init__(self):
        if self.token_estimate == 0:
            self.token_estimate = len(self.content) // 4


class BaselineGenerator:
    """Generates structured baseline documents for Grok discussions."""
    
    def __init__(self, token_budget: int = 10000):
        """Initialize baseline generator.
        
        Args:
            token_budget: Maximum tokens for baseline document
        """
        self.token_budget = token_budget
        
    async def generate(
        self,
        topic: str,
        analysis: Dict[str, Any],
        context_items: List[ContextItem],
        use_expert_mode: bool = False
    ) -> str:
        """Generate a comprehensive baseline document.
        
        Args:
            topic: Discussion topic
            analysis: Question analysis results
            context_items: Gathered context items
            use_expert_mode: Whether to include expert perspectives
            
        Returns:
            Formatted baseline document
        """
        logger.info(f"Generating baseline document for topic: {topic}")
        
        sections = []
        
        # 1. Executive Summary
        sections.append(BaselineSection(
            title="Executive Summary",
            content=self._create_executive_summary(topic, analysis),
            priority=1
        ))
        
        # 2. Problem Analysis
        sections.append(BaselineSection(
            title="Problem Analysis",
            content=self._analyze_problem(topic, analysis),
            priority=1
        ))
        
        # 3. Current Context
        if context_items:
            sections.append(BaselineSection(
                title="Current Implementation Context",
                content=self._summarize_context(context_items),
                priority=2
            ))
        
        # 4. Technical Requirements
        sections.append(BaselineSection(
            title="Technical Requirements",
            content=self._extract_requirements(topic, analysis),
            priority=2
        ))
        
        # 5. Expert Perspectives (if enabled)
        if use_expert_mode:
            sections.append(BaselineSection(
                title="Expert Perspectives",
                content=self._gather_expert_perspectives(topic, analysis),
                priority=3
            ))
        
        # 6. Proposed Approach
        sections.append(BaselineSection(
            title="Proposed Approach",
            content=self._suggest_approach(topic, analysis),
            priority=2
        ))
        
        # 7. Key Questions
        sections.append(BaselineSection(
            title="Key Questions for Discussion",
            content=self._generate_questions(topic, analysis),
            priority=1
        ))
        
        # 8. Success Criteria
        sections.append(BaselineSection(
            title="Success Criteria",
            content=self._define_success_criteria(topic, analysis),
            priority=2
        ))
        
        # Assemble document within token budget
        return self._assemble_document(sections, topic)
    
    def _create_executive_summary(self, topic: str, analysis: Dict[str, Any]) -> str:
        """Create an executive summary of the discussion topic.
        
        Args:
            topic: Discussion topic
            analysis: Question analysis
            
        Returns:
            Executive summary content
        """
        question_type = analysis.get("type", "general")
        keywords = analysis.get("keywords", [])
        
        summary = f"""This document analyzes the following topic:
**"{topic}"**

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Question Type**: {question_type.capitalize()}
**Key Focus Areas**: {', '.join(keywords[:5]) if keywords else 'General discussion'}

**Purpose**: This baseline document provides a structured foundation for an informed discussion 
with Grok-4, ensuring all relevant context and considerations are captured."""
        
        return summary
    
    def _analyze_problem(self, topic: str, analysis: Dict[str, Any]) -> str:
        """Analyze the problem or topic in detail.
        
        Args:
            topic: Discussion topic
            analysis: Question analysis
            
        Returns:
            Problem analysis content
        """
        question_type = analysis.get("type", "general")
        entities = analysis.get("entities", {})
        
        content = f"""## Problem Statement
{topic}

## Analysis Type
This appears to be a **{question_type}** question."""
        
        if question_type == "implementation":
            content += """

### Implementation Considerations
- **Scope**: What components need to be created or modified?
- **Dependencies**: What existing systems will this interact with?
- **Constraints**: What limitations or requirements must be met?
- **Performance**: What performance characteristics are expected?"""
        
        elif question_type == "debugging":
            content += """

### Debugging Approach
- **Symptoms**: What specific errors or unexpected behaviors are occurring?
- **Reproduction**: Can the issue be consistently reproduced?
- **Impact**: What functionality is affected?
- **Timeline**: When did the issue first appear?"""
        
        elif question_type == "optimization":
            content += """

### Optimization Goals
- **Current Performance**: What are the current metrics?
- **Target Performance**: What improvements are needed?
- **Bottlenecks**: What are the likely performance bottlenecks?
- **Trade-offs**: What trade-offs are acceptable?"""
        
        # Add entity information if present
        if any(entities.values()):
            content += "\n\n### Identified Components"
            if entities.get("functions"):
                content += f"\n- **Functions**: {', '.join(entities['functions'])}"
            if entities.get("classes"):
                content += f"\n- **Classes**: {', '.join(entities['classes'])}"
            if entities.get("files"):
                content += f"\n- **Files**: {', '.join(entities['files'])}"
            if entities.get("modules"):
                content += f"\n- **Modules**: {', '.join(entities['modules'])}"
        
        return content
    
    def _summarize_context(self, context_items: List[ContextItem]) -> str:
        """Summarize the gathered context.
        
        Args:
            context_items: List of context items
            
        Returns:
            Context summary
        """
        content = "## Available Context\n\n"
        content += f"**Total Context Items**: {len(context_items)}\n"
        content += f"**Estimated Tokens**: {sum(item.token_estimate for item in context_items)}\n\n"
        
        # Group by type
        by_type = {}
        for item in context_items:
            if item.type not in by_type:
                by_type[item.type] = []
            by_type[item.type].append(item)
        
        for item_type, items in by_type.items():
            content += f"\n### {item_type.capitalize()} Context ({len(items)} items)\n"
            for item in items[:5]:  # Show top 5 per type
                content += f"- **{item.path}** (relevance: {item.relevance_score:.2f})\n"
                
                # Add brief preview if available
                if item.metadata.get("extension") in [".py", ".js", ".ts"]:
                    # Extract first function or class if possible
                    lines = item.content.split('\n')[:10]
                    preview = '\n'.join(lines[:3])
                    if len(preview) > 100:
                        preview = preview[:100] + "..."
                    content += f"  ```\n  {preview}\n  ```\n"
        
        return content
    
    def _extract_requirements(self, topic: str, analysis: Dict[str, Any]) -> str:
        """Extract technical requirements from the topic.
        
        Args:
            topic: Discussion topic
            analysis: Question analysis
            
        Returns:
            Requirements content
        """
        question_type = analysis.get("type", "general")
        
        content = "## Technical Requirements\n\n"
        
        if question_type == "implementation":
            content += """### Functional Requirements
- Primary functionality to be implemented
- User interactions and workflows
- Data inputs and outputs
- Integration points

### Non-Functional Requirements
- Performance expectations
- Security considerations
- Scalability needs
- Maintainability standards"""
        
        elif question_type == "debugging":
            content += """### Debugging Requirements
- Error messages and stack traces
- System state when error occurs
- Expected vs actual behavior
- Test cases to verify fix"""
        
        elif question_type == "optimization":
            content += """### Performance Requirements
- Current performance metrics
- Target performance goals
- Acceptable resource usage
- Response time requirements"""
        
        else:
            content += """### General Requirements
- Clear problem definition
- Desired outcome
- Constraints and limitations
- Success metrics"""
        
        return content
    
    def _gather_expert_perspectives(self, topic: str, analysis: Dict[str, Any]) -> str:
        """Gather multiple expert perspectives on the topic.
        
        Args:
            topic: Discussion topic
            analysis: Question analysis
            
        Returns:
            Expert perspectives content
        """
        question_type = analysis.get("type", "general")
        
        content = "## Expert Perspectives\n\n"
        
        # Software Architect perspective
        content += """### Software Architect Perspective
- **Architecture Impact**: How does this affect system architecture?
- **Design Patterns**: What patterns could be applied?
- **Scalability**: How will this scale with growth?
- **Maintainability**: How can we ensure long-term maintainability?

"""
        
        # Security Expert perspective
        content += """### Security Expert Perspective
- **Security Risks**: What security vulnerabilities might this introduce?
- **Data Protection**: How is sensitive data handled?
- **Access Control**: What authorization is needed?
- **Audit Trail**: What needs to be logged for security?

"""
        
        # Performance Engineer perspective
        if question_type in ["implementation", "optimization"]:
            content += """### Performance Engineer Perspective
- **Performance Impact**: What is the performance cost?
- **Optimization Opportunities**: Where can we optimize?
- **Caching Strategy**: What can be cached?
- **Resource Usage**: What resources are consumed?

"""
        
        # QA Engineer perspective
        content += """### QA Engineer Perspective
- **Testing Strategy**: How will this be tested?
- **Edge Cases**: What edge cases need consideration?
- **Test Coverage**: What coverage is needed?
- **Regression Risk**: What existing functionality might be affected?"""
        
        return content
    
    def _suggest_approach(self, topic: str, analysis: Dict[str, Any]) -> str:
        """Suggest an approach to addressing the topic.
        
        Args:
            topic: Discussion topic
            analysis: Question analysis
            
        Returns:
            Suggested approach content
        """
        question_type = analysis.get("type", "general")
        
        content = "## Proposed Approach\n\n"
        
        if question_type == "implementation":
            content += """### Implementation Strategy
1. **Planning Phase**
   - Define clear requirements
   - Design component interfaces
   - Identify dependencies

2. **Development Phase**
   - Implement core functionality
   - Write unit tests
   - Handle error cases

3. **Testing Phase**
   - Run unit tests
   - Perform integration testing
   - Validate edge cases

4. **Deployment Phase**
   - Code review
   - Documentation update
   - Deployment preparation"""
        
        elif question_type == "debugging":
            content += """### Debugging Strategy
1. **Reproduce the Issue**
   - Identify steps to reproduce
   - Isolate the problem area
   - Gather error information

2. **Root Cause Analysis**
   - Analyze stack traces
   - Check recent changes
   - Review related components

3. **Develop Fix**
   - Implement targeted solution
   - Add defensive coding
   - Include error handling

4. **Verify Solution**
   - Test the fix
   - Check for regressions
   - Validate edge cases"""
        
        elif question_type == "optimization":
            content += """### Optimization Strategy
1. **Measure Current State**
   - Profile performance
   - Identify bottlenecks
   - Establish baseline metrics

2. **Analyze Opportunities**
   - Algorithm improvements
   - Caching possibilities
   - Resource optimization

3. **Implement Improvements**
   - Apply optimizations
   - Maintain functionality
   - Add performance tests

4. **Validate Results**
   - Measure improvements
   - Compare to targets
   - Check for side effects"""
        
        else:
            content += """### General Approach
1. **Analysis**
   - Understand the problem
   - Gather requirements
   - Research solutions

2. **Design**
   - Plan the solution
   - Consider alternatives
   - Choose best approach

3. **Implementation**
   - Build the solution
   - Test thoroughly
   - Document clearly

4. **Validation**
   - Verify requirements met
   - Get feedback
   - Iterate if needed"""
        
        return content
    
    def _generate_questions(self, topic: str, analysis: Dict[str, Any]) -> str:
        """Generate key questions for the discussion.
        
        Args:
            topic: Discussion topic
            analysis: Question analysis
            
        Returns:
            Questions content
        """
        question_type = analysis.get("type", "general")
        keywords = analysis.get("keywords", [])
        
        content = "## Key Questions for Discussion\n\n"
        
        # Type-specific questions
        if question_type == "implementation":
            content += """### Implementation Questions
1. What is the best architectural pattern for this implementation?
2. How should error handling be structured?
3. What external dependencies are acceptable?
4. How can we ensure the code is testable and maintainable?
5. What performance considerations should be addressed upfront?

"""
        elif question_type == "debugging":
            content += """### Debugging Questions
1. What is the exact error message and stack trace?
2. When did this issue first appear?
3. What recent changes might have caused this?
4. Can this be reproduced consistently?
5. What is the impact on users or system functionality?

"""
        elif question_type == "optimization":
            content += """### Optimization Questions
1. What are the current performance metrics?
2. What is the target performance goal?
3. Which operations are the bottlenecks?
4. What trade-offs are acceptable?
5. How will we measure success?

"""
        
        # General questions
        content += """### General Considerations
1. What are the main risks or challenges?
2. Are there existing solutions or patterns to consider?
3. What is the timeline for this work?
4. Who are the stakeholders?
5. What documentation is needed?"""
        
        # Add keyword-specific questions if relevant
        if keywords:
            content += f"\n\n### Topic-Specific Questions\n"
            for i, keyword in enumerate(keywords[:3], 1):
                content += f"{i}. How does this relate to {keyword}?\n"
        
        return content
    
    def _define_success_criteria(self, topic: str, analysis: Dict[str, Any]) -> str:
        """Define success criteria for the discussion.
        
        Args:
            topic: Discussion topic
            analysis: Question analysis
            
        Returns:
            Success criteria content
        """
        question_type = analysis.get("type", "general")
        
        content = "## Success Criteria\n\n"
        
        content += "### Primary Success Metrics\n"
        
        if question_type == "implementation":
            content += """- [ ] Feature is fully implemented and working
- [ ] All unit tests pass
- [ ] Code is reviewed and approved
- [ ] Documentation is updated
- [ ] No regression in existing functionality"""
        
        elif question_type == "debugging":
            content += """- [ ] Bug is identified and fixed
- [ ] Root cause is understood
- [ ] Fix is tested and verified
- [ ] No new issues introduced
- [ ] Prevention measures documented"""
        
        elif question_type == "optimization":
            content += """- [ ] Performance targets are met
- [ ] No functionality is broken
- [ ] Improvements are measurable
- [ ] Resource usage is acceptable
- [ ] Solution is sustainable"""
        
        else:
            content += """- [ ] Problem is clearly understood
- [ ] Solution is well-designed
- [ ] Implementation is complete
- [ ] Quality standards are met
- [ ] Stakeholders are satisfied"""
        
        content += """

### Secondary Success Indicators
- Clear understanding of trade-offs
- Knowledge transfer completed
- Future improvements identified
- Lessons learned documented
- Team alignment achieved"""
        
        return content
    
    def _assemble_document(self, sections: List[BaselineSection], topic: str) -> str:
        """Assemble the final baseline document within token budget.
        
        Args:
            sections: List of document sections
            topic: Discussion topic
            
        Returns:
            Assembled baseline document
        """
        # Sort sections by priority
        sections.sort(key=lambda x: x.priority)
        
        # Start with header
        document = f"# Baseline Document\n\n"
        document += f"**Topic**: {topic}\n"
        document += f"**Generated**: {datetime.now().isoformat()}\n"
        document += f"**Document Version**: 1.0.0\n\n"
        document += "---\n\n"
        
        # Calculate header tokens
        used_tokens = len(document) // 4
        
        # Add sections within budget
        for section in sections:
            if used_tokens + section.token_estimate <= self.token_budget:
                document += f"## {section.title}\n\n"
                document += section.content
                document += "\n\n"
                used_tokens += section.token_estimate
            else:
                # Try to add truncated version
                remaining_tokens = self.token_budget - used_tokens
                if remaining_tokens > 200:
                    truncated = section.content[:remaining_tokens * 4]
                    document += f"## {section.title}\n\n"
                    document += truncated
                    document += "\n... (section truncated to fit token budget)\n\n"
                    break
        
        # Add footer
        document += "---\n\n"
        document += f"*Document contains approximately {used_tokens} tokens*\n"
        
        logger.info(f"Generated baseline document with {used_tokens} tokens")
        return document