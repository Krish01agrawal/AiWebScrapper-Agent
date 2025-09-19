import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.agents.base import BaseAgent
from app.agents.schemas import QueryCategory, AIToolsQuery, MutualFundsQuery, GeneralQuery
from app.agents.prompts import prompt_manager
from app.core.gemini import GeminiClient
from app.core.config import Settings

logger = logging.getLogger(__name__)


class NaturalLanguageParser(BaseAgent):
    """Natural language parser that uses Gemini to extract intent and entities."""
    
    def __init__(
        self,
        gemini_client: GeminiClient,
        settings: Optional[Settings] = None
    ):
        super().__init__(
            name="NaturalLanguageParser",
            description="Parses natural language queries using Gemini AI",
            version="1.0.0",
            gemini_client=gemini_client,
            settings=settings
        )
    
    async def execute(self, query_text: str) -> Dict[str, Any]:
        """Parse a natural language query and extract structured information."""
        start_time = datetime.utcnow()
        
        try:
            # Create the parsing prompt using PromptManager
            prompt = self._create_parsing_prompt(query_text)
            
            # Get response from Gemini
            response = await self.gemini_client.generate_content(
                prompt,
                generation_config={
                    "temperature": self.settings.gemini_temperature,
                    "max_output_tokens": self.settings.gemini_max_tokens,
                }
            )
            
            # Parse the response
            parsed_data = await self._parse_gemini_response(response.text)
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Add metadata
            parsed_data["processing_time"] = processing_time
            parsed_data["raw_query"] = query_text
            
            logger.info(f"Successfully parsed query in {processing_time:.2f}s")
            return parsed_data
            
        except Exception as e:
            logger.error(f"Failed to parse query: {str(e)}")
            raise
    
    def _create_parsing_prompt(self, query_text: str) -> str:
        """Create the prompt for parsing the query using PromptManager."""
        template = prompt_manager.get_template("intent_extraction")
        if template:
            return template.format(query=query_text)
        else:
            # Fallback to original prompt if template not found
            return f"""Analyze the following user query and extract the key information:

Query: {query_text}

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
}}"""
    
    async def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the Gemini response into structured data using async JSON parsing."""
        try:
            # Try to extract JSON from the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end != 0:
                json_str = response_text[json_start:json_end]
                
                # Use asyncio.to_thread() to prevent blocking the event loop
                # Add size limit to prevent blocking with large responses
                if len(json_str) > 10000:  # 10KB limit
                    logger.warning("JSON response too large, using fallback parsing")
                    return self._fallback_parsing(response_text)
                
                parsed = await asyncio.to_thread(json.loads, json_str)
                
                # Validate and clean the parsed data
                return self._validate_parsed_data(parsed)
            else:
                raise ValueError("No JSON found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            # Fallback to basic parsing
            return self._fallback_parsing(response_text)
    
    def _validate_parsed_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean the parsed data."""
        # Ensure required fields exist with default values
        if "intent" not in data:
            data["intent"] = "query_processing"
        if "entities" not in data:
            data["entities"] = []
        if "domain" not in data:
            data["domain"] = "general"
        if "confidence" not in data:
            data["confidence"] = 0.5
        
        # Validate confidence score
        if data.get("confidence") is not None:
            try:
                confidence = float(data["confidence"])
                data["confidence"] = max(0.0, min(1.0, confidence))
            except (ValueError, TypeError):
                data["confidence"] = 0.5
        
        # Ensure entities is a list
        if not isinstance(data.get("entities"), list):
            data["entities"] = []
        
        return data
    
    def _fallback_parsing(self, response_text: str) -> Dict[str, Any]:
        """Fallback parsing when JSON extraction fails."""
        logger.info("Using fallback parsing for response")
        
        # Basic keyword-based parsing
        response_lower = response_text.lower()
        
        # Determine domain based on keywords
        domain = "general"
        if any(keyword in response_lower for keyword in ["ai", "artificial intelligence", "tool", "generation"]):
            domain = "ai_tools"
        elif any(keyword in response_lower for keyword in ["mutual fund", "investment", "finance", "money"]):
            domain = "mutual_funds"
        
        return {
            "intent": "query_processing",
            "entities": [],
            "domain": domain,
            "confidence": 0.3,
            "additional_context": "Fallback parsing used",
            "raw_response": response_text
        }
    
    async def parse_query(self, query_text: str) -> Dict[str, Any]:
        """Main method to parse a query with timeout handling."""
        return await self.execute_with_timeout(query_text)
