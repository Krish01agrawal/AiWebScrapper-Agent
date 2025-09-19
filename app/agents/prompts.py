from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    """Template for managing reusable prompt templates."""
    
    name: str
    template: str
    version: str = "1.0.0"
    variables: Optional[Dict[str, str]] = None
    examples: Optional[list] = None
    description: Optional[str] = None
    
    def format(self, **kwargs) -> str:
        """Format the template with provided variables."""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required variable for template '{self.name}': {e}")
    
    def get_variables(self) -> set:
        """Get the set of variables used in this template."""
        import string
        formatter = string.Formatter()
        return {field_name for _, field_name, _, _ in formatter.parse(self.template) if field_name}


class PromptManager:
    """Centralized prompt management system."""
    
    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}
        self._initialize_default_prompts()
    
    def _initialize_default_prompts(self):
        """Initialize default prompt templates."""
        
        # Query parsing prompts
        self.add_template(PromptTemplate(
            name="intent_extraction",
            version="1.0.0",
            description="Extract intent and entities from user queries",
            template="""Analyze the following user query and extract the key information:

Query: {query}

Please provide a structured response with:
1. Primary intent
2. Key entities mentioned
3. Domain/category (AI tools, mutual funds, general, etc.)
4. Confidence level (0.0-1.0)

Respond in JSON format:
{{
    "intent": "string",
    "entities": ["list", "of", "entities"],
    "domain": "string",
    "confidence": 0.95,
    "additional_context": "string"
}}""",
            examples=[
                {
                    "query": "Find AI tools for image generation",
                    "response": {
                        "intent": "search for AI tools",
                        "entities": ["AI tools", "image generation"],
                        "domain": "ai_tools",
                        "confidence": 0.95,
                        "additional_context": "User wants to find AI-powered image generation tools"
                    }
                }
            ]
        ))
        
        # AI tools categorization
        self.add_template(PromptTemplate(
            name="ai_tools_categorization",
            version="1.0.0",
            description="Categorize AI tools related queries",
            template="""Analyze this AI tools query and extract structured information:

Query: {query}

Extract the following information in JSON format:
{{
    "tool_type": "string (e.g., image generation, text analysis, code generation)",
    "use_case": "string (primary use case)",
    "features_required": ["list", "of", "required", "features"],
    "budget_range": "string (free, low, medium, high)",
    "technical_expertise": "string (beginner, intermediate, advanced)"
}}""",
            examples=[
                {
                    "query": "I need an AI tool for creating logos",
                    "response": {
                        "tool_type": "logo generation",
                        "use_case": "brand identity creation",
                        "features_required": ["logo design", "brand customization"],
                        "budget_range": "medium",
                        "technical_expertise": "beginner"
                    }
                }
            ]
        ))
        
        # Mutual funds categorization
        self.add_template(PromptTemplate(
            name="mutual_funds_categorization",
            version="1.0.0",
            description="Categorize mutual funds related queries",
            template="""Analyze this mutual funds query and extract structured information:

Query: {query}

Extract the following information in JSON format:
{{
    "investment_type": "string (equity, debt, hybrid, sector-specific)",
    "risk_level": "string (low, medium, high)",
    "time_horizon": "string (short-term, medium-term, long-term)",
    "amount_range": "string (small, medium, large)",
    "investment_goal": "string (wealth creation, income, tax saving)"
}}""",
            examples=[
                {
                    "query": "I want to invest in equity mutual funds for long term",
                    "response": {
                        "investment_type": "equity",
                        "risk_level": "high",
                        "time_horizon": "long-term",
                        "amount_range": "medium",
                        "investment_goal": "wealth creation"
                    }
                }
            ]
        ))
        
        # General query categorization
        self.add_template(PromptTemplate(
            name="general_categorization",
            version="1.0.0",
            description="Categorize general queries",
            template="""Analyze this general query and extract structured information:

Query: {query}

Extract the following information in JSON format:
{{
    "intent": "string (what the user wants to achieve)",
    "entities": ["list", "of", "key", "entities"],
    "context": "string (additional context or details)",
    "category": "string (general domain if identifiable)"
}}""",
            examples=[
                {
                    "query": "How do I learn Python programming?",
                    "response": {
                        "intent": "learn programming language",
                        "entities": ["Python", "programming"],
                        "context": "User wants to start learning Python",
                        "category": "education"
                    }
                }
            ]
        ))
    
    def add_template(self, template: PromptTemplate):
        """Add a new prompt template."""
        self.templates[template.name] = template
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get a prompt template by name."""
        return self.templates.get(name)
    
    def list_templates(self) -> list:
        """List all available template names."""
        return list(self.templates.keys())
    
    def validate_template_variables(self, template_name: str, provided_vars: Dict[str, Any]) -> bool:
        """Validate that all required template variables are provided."""
        template = self.get_template(template_name)
        if not template:
            return False
        
        required_vars = template.get_variables()
        provided_keys = set(provided_vars.keys())
        
        return required_vars.issubset(provided_keys)
    
    def get_template_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a template."""
        template = self.get_template(name)
        if not template:
            return None
        
        return {
            "name": template.name,
            "version": template.version,
            "description": template.description,
            "variables": list(template.get_variables()),
            "examples_count": len(template.examples) if template.examples else 0
        }


# Global prompt manager instance
prompt_manager = PromptManager()
