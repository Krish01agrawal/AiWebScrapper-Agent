import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.agents.base import BaseAgent
from app.agents.schemas import (
    QueryCategory, BaseQueryResult, AIToolsQuery, MutualFundsQuery, 
    GeneralQuery, ParsedQuery
)
from app.agents.parsers import NaturalLanguageParser
from app.agents.categorizer import DomainCategorizer
from app.agents.prompts import prompt_manager
from app.core.gemini import GeminiClient
from app.core.config import Settings

logger = logging.getLogger(__name__)


class QueryProcessor(BaseAgent):
    """Main query processor that orchestrates the entire workflow."""
    
    def __init__(
        self,
        gemini_client: GeminiClient,
        settings: Optional[Settings] = None
    ):
        super().__init__(
            name="QueryProcessor",
            description="Orchestrates query parsing, categorization, and schema mapping",
            version="1.0.0",
            gemini_client=gemini_client,
            settings=settings
        )
        
        # Initialize components
        self.parser = NaturalLanguageParser(gemini_client, settings)
        self.categorizer = DomainCategorizer(gemini_client, settings)
    
    async def execute(self, query_text: str) -> ParsedQuery:
        """Process a query through the complete workflow."""
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Starting query processing for: {query_text[:100]}...")
            
            # Step 1: Parse the query
            parsed_data = await self.parser.parse_query(query_text)
            logger.info("Query parsing completed")
            
            # Step 2: Categorize the query
            category, confidence = await self.categorizer.categorize_query(parsed_data)
            logger.info(f"Query categorized as {category} with confidence {confidence:.2f}")
            
            # Step 3: Map to domain-specific schemas
            domain_data = await self._map_to_domain_schema(category, parsed_data)
            logger.info("Domain schema mapping completed")
            
            # Step 4: Create the final result
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            result = self._create_parsed_query(
                query_text=query_text,
                category=category,
                confidence=confidence,
                processing_time=processing_time,
                parsed_data=parsed_data,
                domain_data=domain_data
            )
            
            logger.info(f"Query processing completed in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Query processing failed: {str(e)}")
            # Return error result
            return self._create_error_result(query_text, str(e), start_time)
    
    async def _map_to_domain_schema(
        self, 
        category: QueryCategory, 
        parsed_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Map parsed data to domain-specific schemas."""
        try:
            if category == QueryCategory.AI_TOOLS:
                return await self._extract_ai_tools_data(parsed_data)
            elif category == QueryCategory.MUTUAL_FUNDS:
                return await self._extract_mutual_funds_data(parsed_data)
            elif category == QueryCategory.GENERAL:
                return await self._extract_general_data(parsed_data)
            else:
                return None
        except Exception as e:
            logger.warning(f"Failed to map to domain schema: {e}")
            return None
    
    async def _extract_ai_tools_data(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract AI tools specific data using Gemini."""
        try:
            prompt = self._create_ai_tools_prompt(parsed_data)
            
            response = await self.gemini_client.generate_content(
                prompt,
                generation_config={
                    "temperature": self.settings.gemini_temperature,
                    "max_output_tokens": 800,
                }
            )
            
            return await self._parse_ai_tools_response(response.text)
            
        except Exception as e:
            logger.warning(f"AI tools data extraction failed: {e}")
            return self._fallback_ai_tools_data(parsed_data)
    
    def _create_ai_tools_prompt(self, parsed_data: Dict[str, Any]) -> str:
        """Create prompt for AI tools data extraction using PromptManager."""
        query_text = parsed_data.get("raw_query", "")
        intent = parsed_data.get("intent", "")
        entities = parsed_data.get("entities", [])
        
        # Try to use the AI tools categorization template
        template = prompt_manager.get_template("ai_tools_categorization")
        if template:
            return template.format(query=query_text)
        else:
            # Fallback to original prompt if template not found
            return f"""Analyze this AI tools query and extract structured information:

Query: {query_text}
Intent: {intent}
Entities: {', '.join(entities)}

Extract the following information in JSON format:
{{
    "tool_type": "string (e.g., image generation, text analysis, code generation)",
    "use_case": "string (primary use case)",
    "features_required": ["list", "of", "required", "features"],
    "budget_range": "string (free, low, medium, high)",
    "technical_expertise": "string (beginner, intermediate, advanced)"
}}"""
    
    async def _parse_ai_tools_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the AI tools response using async JSON parsing."""
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end != 0:
                json_str = response_text[json_start:json_end]
                
                # Use asyncio.to_thread() to prevent blocking the event loop
                # Add size limit to prevent blocking with large responses
                if len(json_str) > 8000:  # 8KB limit for AI tools responses
                    logger.warning("JSON response too large, using fallback AI tools data")
                    return {}
                
                return await asyncio.to_thread(json.loads, json_str)
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            logger.warning(f"Failed to parse AI tools response: {e}")
            return {}
    
    def _fallback_ai_tools_data(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback AI tools data extraction."""
        query_lower = parsed_data.get("raw_query", "").lower()
        
        # Basic keyword extraction
        tool_type = "general"
        if "image" in query_lower or "logo" in query_lower:
            tool_type = "image generation"
        elif "text" in query_lower or "writing" in query_lower:
            tool_type = "text generation"
        elif "code" in query_lower or "programming" in query_lower:
            tool_type = "code generation"
        
        return {
            "tool_type": tool_type,
            "use_case": "general purpose",
            "features_required": [],
            "budget_range": "medium",
            "technical_expertise": "beginner"
        }
    
    async def _extract_mutual_funds_data(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract mutual funds specific data using Gemini."""
        try:
            prompt = self._create_mutual_funds_prompt(parsed_data)
            
            response = await self.gemini_client.generate_content(
                prompt,
                generation_config={
                    "temperature": self.settings.gemini_temperature,
                    "max_output_tokens": 800,
                }
            )
            
            return await self._parse_mutual_funds_response(response.text)
            
        except Exception as e:
            logger.warning(f"Mutual funds data extraction failed: {e}")
            return self._fallback_mutual_funds_data(parsed_data)
    
    def _create_mutual_funds_prompt(self, parsed_data: Dict[str, Any]) -> str:
        """Create prompt for mutual funds data extraction using PromptManager."""
        query_text = parsed_data.get("raw_query", "")
        intent = parsed_data.get("intent", "")
        entities = parsed_data.get("entities", [])
        
        # Try to use the mutual funds categorization template
        template = prompt_manager.get_template("mutual_funds_categorization")
        if template:
            return template.format(query=query_text)
        else:
            # Fallback to original prompt if template not found
            return f"""Analyze this mutual funds query and extract structured information:

Query: {query_text}
Intent: {intent}
Entities: {', '.join(entities)}

Extract the following information in JSON format:
{{
    "investment_type": "string (equity, debt, hybrid, sector-specific)",
    "risk_level": "string (low, medium, high)",
    "time_horizon": "string (short-term, medium-term, long-term)",
    "amount_range": "string (small, medium, large)",
    "investment_goal": "string (wealth creation, income, tax saving)"
}}"""
    
    async def _parse_mutual_funds_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the mutual funds response using async JSON parsing."""
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end != 0:
                json_str = response_text[json_start:json_end]
                
                # Use asyncio.to_thread() to prevent blocking the event loop
                # Add size limit to prevent blocking with large responses
                if len(json_str) > 8000:  # 8KB limit for mutual funds responses
                    logger.warning("JSON response too large, using fallback mutual funds data")
                    return {}
                
                return await asyncio.to_thread(json.loads, json_str)
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            logger.warning(f"Failed to parse mutual funds response: {e}")
            return {}
    
    def _fallback_mutual_funds_data(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback mutual funds data extraction."""
        query_lower = parsed_data.get("raw_query", "").lower()
        
        # Basic keyword extraction
        investment_type = "equity"
        if "debt" in query_lower or "bond" in query_lower:
            investment_type = "debt"
        elif "hybrid" in query_lower or "balanced" in query_lower:
            investment_type = "hybrid"
        
        return {
            "investment_type": investment_type,
            "risk_level": "medium",
            "time_horizon": "long-term",
            "amount_range": "medium",
            "investment_goal": "wealth creation"
        }
    
    async def _extract_general_data(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract general query data."""
        return {
            "intent": parsed_data.get("intent", "query_processing"),
            "entities": parsed_data.get("entities", []),
            "context": parsed_data.get("additional_context", ""),
            "category": "general"
        }
    
    def _create_parsed_query(
        self,
        query_text: str,
        category: QueryCategory,
        confidence: float,
        processing_time: float,
        parsed_data: Dict[str, Any],
        domain_data: Optional[Dict[str, Any]]
    ) -> ParsedQuery:
        """Create the final ParsedQuery object."""
        # Create base result
        base_result = BaseQueryResult(
            query_text=query_text,
            confidence_score=confidence,
            processing_time=processing_time,
            category=category
        )
        
        # Create domain-specific data
        ai_tools_data = None
        mutual_funds_data = None
        general_data = None
        
        if category == QueryCategory.AI_TOOLS and domain_data:
            ai_tools_data = AIToolsQuery(**domain_data)
        elif category == QueryCategory.MUTUAL_FUNDS and domain_data:
            mutual_funds_data = MutualFundsQuery(**domain_data)
        elif category == QueryCategory.GENERAL and domain_data:
            general_data = GeneralQuery(**domain_data)
        
        # Create suggestions
        suggestions = self._generate_suggestions(category, confidence, domain_data)
        
        return ParsedQuery(
            base_result=base_result,
            ai_tools_data=ai_tools_data,
            mutual_funds_data=mutual_funds_data,
            general_data=general_data,
            raw_entities=parsed_data,
            suggestions=suggestions
        )
    
    def _generate_suggestions(
        self, 
        category: QueryCategory, 
        confidence: float, 
        domain_data: Optional[Dict[str, Any]]
    ) -> list:
        """Generate follow-up suggestions based on the query."""
        suggestions = []
        
        if confidence < 0.7:
            suggestions.append("Consider providing more specific details for better results")
        
        if category == QueryCategory.AI_TOOLS:
            suggestions.append("Specify your budget range for more targeted recommendations")
            suggestions.append("Mention your technical expertise level")
        elif category == QueryCategory.MUTUAL_FUNDS:
            suggestions.append("Consider your risk tolerance and investment timeline")
            suggestions.append("Specify your investment amount range")
        
        suggestions.append("Ask follow-up questions for more detailed information")
        
        return suggestions
    
    def _create_error_result(self, query_text: str, error_message: str, start_time: datetime) -> ParsedQuery:
        """Create an error result when processing fails."""
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        base_result = BaseQueryResult(
            query_text=query_text,
            confidence_score=0.0,
            processing_time=processing_time,
            category=QueryCategory.UNKNOWN
        )
        
        return ParsedQuery(
            base_result=base_result,
            suggestions=[f"Processing failed: {error_message}", "Please try rephrasing your query"]
        )
    
    async def process_query(self, query_text: str) -> ParsedQuery:
        """Main method to process a query with timeout handling."""
        return await self.execute_with_timeout(query_text)
