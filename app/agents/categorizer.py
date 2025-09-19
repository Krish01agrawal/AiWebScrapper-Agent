import json
import asyncio
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from app.agents.base import BaseAgent
from app.agents.schemas import QueryCategory
from app.agents.prompts import prompt_manager
from app.core.gemini import GeminiClient
from app.core.config import Settings

logger = logging.getLogger(__name__)


class DomainCategorizer(BaseAgent):
    """Domain categorizer that determines query types using rules and LLM."""
    
    def __init__(
        self,
        gemini_client: GeminiClient,
        settings: Optional[Settings] = None
    ):
        super().__init__(
            name="DomainCategorizer",
            description="Categorizes queries into domains using rules and LLM",
            version="1.0.0",
            gemini_client=gemini_client,
            settings=settings
        )
        self._initialize_keyword_rules()
    
    def _initialize_keyword_rules(self):
        """Initialize keyword-based categorization rules."""
        self.keyword_rules = {
            QueryCategory.AI_TOOLS: [
                "ai", "artificial intelligence", "machine learning", "ml", "neural network",
                "deep learning", "nlp", "computer vision", "image generation", "text generation",
                "code generation", "chatbot", "automation", "algorithm", "model", "training",
                "inference", "prediction", "classification", "regression", "clustering"
            ],
            QueryCategory.MUTUAL_FUNDS: [
                "mutual fund", "investment", "finance", "money", "portfolio", "asset",
                "equity", "debt", "hybrid", "sector", "index", "etf", "dividend",
                "capital gains", "risk", "return", "volatility", "diversification",
                "financial planning", "retirement", "tax saving", "wealth creation"
            ]
        }
    
    async def execute(self, parsed_data: Dict[str, Any]) -> Tuple[QueryCategory, float]:
        """Categorize a parsed query and return category with confidence."""
        start_time = datetime.utcnow()
        
        try:
            # First try rule-based categorization
            category, confidence = self._rule_based_categorization(parsed_data)
            
            # If confidence is low, use LLM categorization
            if confidence < self.settings.agent_confidence_threshold:
                logger.info("Low confidence in rule-based categorization, using LLM")
                category, confidence = await self._llm_categorization(parsed_data)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Categorized query as {category} with confidence {confidence:.2f} in {processing_time:.2f}s")
            
            return category, confidence
            
        except Exception as e:
            logger.error(f"Failed to categorize query: {str(e)}")
            # Return unknown category with low confidence
            return QueryCategory.UNKNOWN, 0.1
    
    def _rule_based_categorization(self, parsed_data: Dict[str, Any]) -> Tuple[QueryCategory, float]:
        """Use keyword rules to categorize the query."""
        query_text = parsed_data.get("raw_query", "").lower()
        entities = [entity.lower() for entity in parsed_data.get("entities", [])]
        
        # Check all text content
        all_text = query_text + " " + " ".join(entities)
        
        scores = {}
        for category, keywords in self.keyword_rules.items():
            score = 0
            for keyword in keywords:
                if keyword in all_text:
                    score += 1
            
            if score > 0:
                # Normalize score based on number of keywords
                scores[category] = min(0.9, score / len(keywords) + 0.3)
        
        if not scores:
            return QueryCategory.GENERAL, 0.4
        
        # Return category with highest score
        best_category = max(scores.keys(), key=lambda k: scores[k])
        confidence = scores[best_category]
        
        return best_category, confidence
    
    async def _llm_categorization(self, parsed_data: Dict[str, Any]) -> Tuple[QueryCategory, float]:
        """Use LLM to categorize ambiguous queries."""
        try:
            prompt = self._create_categorization_prompt(parsed_data)
            
            response = await self.gemini_client.generate_content(
                prompt,
                generation_config={
                    "temperature": self.settings.gemini_temperature,
                    "max_output_tokens": 500,
                }
            )
            
            return await self._parse_categorization_response(response.text)
            
        except Exception as e:
            logger.warning(f"LLM categorization failed: {e}, falling back to general")
            return QueryCategory.GENERAL, 0.5
    
    def _create_categorization_prompt(self, parsed_data: Dict[str, Any]) -> str:
        """Create the prompt for LLM categorization using PromptManager."""
        query_text = parsed_data.get("raw_query", "")
        intent = parsed_data.get("intent", "")
        entities = parsed_data.get("entities", [])
        
        # Try to use the general categorization template
        template = prompt_manager.get_template("general_categorization")
        if template:
            return template.format(query=query_text)
        else:
            # Fallback to original prompt if template not found
            return f"""Analyze this query and categorize it into one of these domains:

Query: {query_text}
Intent: {intent}
Entities: {', '.join(entities)}

Available categories:
1. ai_tools - For AI, machine learning, automation, and technology tools
2. mutual_funds - For investment, finance, and financial planning
3. general - For other topics not fitting the above categories

Respond with JSON:
{{
    "category": "ai_tools|mutual_funds|general",
    "confidence": 0.85,
    "reasoning": "Brief explanation of categorization"
}}"""
    
    async def _parse_categorization_response(self, response_text: str) -> Tuple[QueryCategory, float]:
        """Parse the LLM categorization response using async JSON parsing."""
        try:
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end != 0:
                json_str = response_text[json_start:json_end]
                
                # Use asyncio.to_thread() to prevent blocking the event loop
                # Add size limit to prevent blocking with large responses
                if len(json_str) > 5000:  # 5KB limit for categorization responses
                    logger.warning("JSON response too large, using fallback categorization")
                    return QueryCategory.GENERAL, 0.5
                
                parsed = await asyncio.to_thread(json.loads, json_str)
                
                category_str = parsed.get("category", "general")
                confidence = float(parsed.get("confidence", 0.5))
                
                # Map string to enum
                category_map = {
                    "ai_tools": QueryCategory.AI_TOOLS,
                    "mutual_funds": QueryCategory.MUTUAL_FUNDS,
                    "general": QueryCategory.GENERAL
                }
                
                category = category_map.get(category_str, QueryCategory.GENERAL)
                confidence = max(0.1, min(1.0, confidence))
                
                return category, confidence
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            logger.warning(f"Failed to parse LLM categorization response: {e}")
            return QueryCategory.GENERAL, 0.5
    
    async def categorize_query(self, parsed_data: Dict[str, Any]) -> Tuple[QueryCategory, float]:
        """Main method to categorize a query with timeout handling."""
        return await self.execute_with_timeout(parsed_data)
