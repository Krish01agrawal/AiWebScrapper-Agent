"""
Base AI Agent module providing common functionality for AI-powered processing agents.
"""
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Generic, TypeVar, Optional
from app.core.gemini import GeminiClient
from app.core.config import get_settings

T = TypeVar('T')

class AIAgentErrorHandler:
    """Standardized error handling for AI agents."""
    
    def __init__(self, agent_name: str):
        """Initialize error handler with error tracking."""
        self.agent_name = agent_name
        self.error_counts = {
            "json_parsing": 0,
            "validation": 0,
            "api_error": 0
        }
    
    @staticmethod
    def handle_ai_error(error: Exception, context: str) -> str:
        """Handle AI-related errors and return user-friendly message."""
        if "API key" in str(error).lower():
            return f"AI service authentication failed: {str(error)}"
        elif "quota" in str(error).lower():
            return f"AI service quota exceeded: {str(error)}"
        elif "network" in str(error).lower() or "connection" in str(error).lower():
            return f"AI service connection failed: {str(error)}"
        else:
            return f"AI processing error in {context}: {str(error)}"
    
    def handle_json_parsing_error(self, raw: str, error: Exception, context: str) -> Dict[str, Any]:
        """Handle JSON parsing errors and return structured error information."""
        self.error_counts["json_parsing"] += 1
        
        return {
            "error_type": "json_parsing",
            "error_message": str(error),
            "raw_content": raw[:200] + "..." if len(raw) > 200 else raw,
            "context": context,
            "error_count": self.error_counts["json_parsing"],
            "fallback": True,
            "error_recovery": True
        }
    
    def handle_validation_error(self, data: Dict[str, Any], error: Exception, context: str) -> Dict[str, Any]:
        """Handle validation errors and return structured error information."""
        self.error_counts["validation"] += 1
        
        return {
            "error_type": "validation",
            "error_message": str(error),
            "invalid_data": data,
            "context": context,
            "error_count": self.error_counts["validation"],
            "fallback": True,
            "error_recovery": True
        }

class BaseAIAgent(ABC, Generic[T]):
    """Base class for AI-powered processing agents using Gemini."""
    
    def __init__(self, name: str, gemini_client: Optional[GeminiClient] = None):
        self.name = name
        self.gemini_client = gemini_client
        self.settings = get_settings()
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    async def process_with_ai(self, content: str, query, **kwargs) -> T:
        """
        Orchestrate the AI processing workflow: prompt building, AI call, parsing, validation, and confidence scoring.
        
        Args:
            content: Content to process
            query: Query context for processing
            **kwargs: Additional context parameters
            
        Returns:
            Processed result of type T
        """
        try:
            # Build the prompt
            prompt = self._build_prompt(content, query, **kwargs)
            
            # Get AI response
            raw_response = await self._get_ai_response(prompt, content)
            
            # Parse the response
            parsed_data = await self._parse_ai_response(raw_response, query, content)
            
            # Validate the response
            validated_data = self._validate_response(parsed_data, query)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(validated_data, query)
            
            # Create the final result
            result = self._create_result(validated_data, confidence_score, query)
            
            return result
            
        except Exception as e:
            self.logger.error(f"AI processing failed: {str(e)}")
            # Return fallback response
            return self.create_fallback_response(query, str(e))
    
    @abstractmethod
    def _build_prompt(self, content: str, query, **kwargs) -> str:
        """Build the prompt for AI processing."""
        pass
    
    @abstractmethod
    async def _get_ai_response(self, prompt: str, context: str) -> str:
        """Get response from AI service."""
        pass
    
    @abstractmethod
    async def _parse_ai_response(self, raw_response: str, query, context: str) -> Dict[str, Any]:
        """Parse raw AI response into structured data."""
        pass
    
    @abstractmethod
    def _validate_response(self, parsed_data: Dict[str, Any], query) -> Dict[str, Any]:
        """Validate parsed AI response data."""
        pass
    
    @abstractmethod
    def _calculate_confidence_score(self, validated_data: Dict[str, Any], query) -> float:
        """Calculate confidence score for the AI response."""
        pass
    
    @abstractmethod
    def _create_result(self, validated_data: Dict[str, Any], confidence_score: float, query) -> T:
        """Create the final result object from validated data."""
        pass
    
    @abstractmethod
    def create_fallback_response(self, query, error_message: str) -> T:
        """Create a fallback response when AI processing fails."""
        pass
    
    def _parse_json_safely(self, raw: str, context: str) -> Dict[str, Any]:
        """
        Safely extract JSON from raw AI response.
        
        Args:
            raw: Raw AI response text
            context: Context for error messages
            
        Returns:
            Parsed JSON data as dictionary
        """
        try:
            # First try to find fenced JSON blocks
            json_block_match = re.search(r'```json\s*(.*?)\s*```', raw, re.DOTALL)
            if json_block_match:
                json_text = json_block_match.group(1).strip()
                return json.loads(json_text)
            
            # Try to find JSON object with braces
            brace_start = raw.find('{')
            if brace_start != -1:
                # Find matching closing brace
                brace_count = 0
                brace_end = -1
                
                for i, char in enumerate(raw[brace_start:], brace_start):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            brace_end = i + 1
                            break
                
                if brace_end != -1:
                    json_text = raw[brace_start:brace_end]
                    return json.loads(json_text)
            
            # Try parsing the entire response as JSON
            return json.loads(raw.strip())
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from AI response: {str(e)}")
            self.logger.debug(f"Raw response: {raw[:500]}...")
            raise ValueError(f"Invalid JSON response from AI: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error parsing AI response: {str(e)}")
            raise
