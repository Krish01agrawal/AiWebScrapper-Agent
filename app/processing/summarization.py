import time
from typing import Dict, Any, List, Optional
from app.processing.ai_agent_base import BaseAIAgent
from app.agents.schemas import ParsedQuery
from app.processing.schemas import ContentSummary, ProcessingError
from app.core.gemini import GeminiClient
from app.core.config import get_settings
from app.processing.prompts import ProcessingPrompts


class SummarizationAgent(BaseAIAgent[ContentSummary]):
    """Content summarization agent for generating structured summaries using Gemini with standardized error handling."""
    
    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        super().__init__("SummarizationAgent", gemini_client)
    
    async def summarize_content(
        self, 
        content: str, 
        query: ParsedQuery,
        title: str = "",
        max_length: Optional[int] = None
    ) -> ContentSummary:
        """
        Generate comprehensive content summary using Gemini AI.
        
        Args:
            content: Content to summarize
            query: Original query context for focus
            title: Content title for context
            max_length: Maximum summary length (uses config default if None)
            
        Returns:
            ContentSummary object with multiple summary levels
        """
        start_time = time.time()
        
        if max_length is None:
            max_length = getattr(self.settings, 'processing_max_summary_length', 500)
        
        try:
            self.logger.info("Starting content summarization")
            
            # Check if Gemini client is available
            if not self.gemini_client:
                self.logger.warning("Gemini client not available, returning fallback summary")
                return self.create_fallback_response(query, "Gemini client not available")
            
            # Process content with AI using standardized methods
            summary = await self.process_with_ai(content, query, title=title, max_length=max_length)
            
            # Validate summary length
            summary = self._validate_summary_length(summary, max_length)
            
            processing_time = time.time() - start_time
            self.logger.info(f"Content summarization completed in {processing_time:.2f}s")
            
            return summary
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Content summarization failed: {str(e)}")
            
            # Return fallback summary using standardized method
            return self.create_fallback_response(query, str(e))
    
    def _build_prompt(self, content: str, query: ParsedQuery, **kwargs) -> str:
        """Build comprehensive summarization prompt using centralized ProcessingPrompts."""
        title = kwargs.get('title', '')
        max_length = kwargs.get('max_length', getattr(self.settings, 'processing_max_summary_length', 500))
        
        return ProcessingPrompts.get_summary_prompt(
            query=query.base_result.query_text,
            category=query.base_result.category.value,
            title=title,
            content=content[:self.settings.gemini_max_content_length],
            max_length=max_length
        )
    
    async def _get_ai_response(self, prompt: str, context: str) -> str:
        """Get AI response from Gemini service."""
        if not self.gemini_client:
            raise RuntimeError("Gemini client not available")
        
        try:
            response = await self.gemini_client.generate_content(prompt)
            return response.text
        except Exception as e:
            self.logger.error(f"Failed to get AI response: {str(e)}")
            raise
    
    async def _parse_ai_response(self, raw_response: str, query: ParsedQuery, context: str) -> Dict[str, Any]:
        """Parse raw AI response into structured data with shared JSON parsing helpers."""
        try:
            # Use shared JSON parsing helper from BaseAIAgent
            parsed_data = self._parse_json_safely(raw_response, context)
            
            # Validate that we have the expected structure
            if isinstance(parsed_data, dict) and any(key in parsed_data for key in ['executive_summary', 'key_points', 'detailed_summary']):
                self.logger.info("Successfully parsed JSON response from AI")
                return parsed_data
            else:
                self.logger.warning("Parsed JSON lacks expected structure, using fallback")
                raise ValueError("Incomplete JSON structure")
                
        except Exception as e:
            self.logger.debug(f"JSON parsing failed, falling back to heuristic parsing: {str(e)}")
            
            # Fallback to heuristic parsing if JSON extraction fails
            parsed_data = {
                "executive_summary": f"Content related to {query.base_result.query_text}",
                "key_points": [f"Content covers {query.base_result.query_text} topics"],
                "detailed_summary": f"This content appears to be related to {query.base_result.query_text}.",
                "main_topics": [query.base_result.query_text],
                "sentiment": "neutral"
            }
            
            # Try to extract actual summary from response if possible
            if "summary:" in raw_response.lower():
                # Basic summary extraction logic
                lines = raw_response.split('\n')
                for line in lines:
                    if "summary" in line.lower() and ":" in line:
                        summary_text = line.split(':')[1].strip()
                        if summary_text and len(summary_text) > 10:
                            parsed_data["detailed_summary"] = summary_text
                            break
            
            return parsed_data
    
    def _validate_response(self, data: Dict[str, Any], query: ParsedQuery) -> Dict[str, Any]:
        """Validate parsed response data and return validated data."""
        try:
            # Ensure all required fields are present
            required_fields = self._get_required_fields()
            for field in required_fields:
                if field not in data:
                    data[field] = self._get_default_value(field)
            
            # Validate data structure
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to validate AI response: {str(e)}")
            # Return fallback data
            return self._get_fallback_data(query, f"Validation failed: {str(e)}")
    
    def _calculate_confidence_score(self, data: Dict[str, Any], query: ParsedQuery) -> float:
        """Calculate confidence score for the AI response."""
        try:
            base_score = 0.5
            
            # Boost based on data completeness
            required_fields = self._get_required_fields()
            completeness = sum(1 for field in required_fields if field in data and data[field]) / len(required_fields)
            base_score += completeness * 0.2
            
            # Boost based on summary quality
            if "detailed_summary" in data and data["detailed_summary"]:
                summary_length = len(data["detailed_summary"])
                if summary_length > 50:
                    base_score += 0.1
                if summary_length > 100:
                    base_score += 0.1
            
            # Boost based on key points
            if "key_points" in data and isinstance(data["key_points"], list) and len(data["key_points"]) > 0:
                base_score += min(len(data["key_points"]) * 0.05, 0.2)
            
            return min(1.0, max(0.0, base_score))
            
        except Exception as e:
            self.logger.error(f"Failed to calculate confidence score: {str(e)}")
            return 0.5
    
    def _get_required_fields(self) -> List[str]:
        """Get list of required fields for ContentSummary."""
        return ["executive_summary", "key_points", "detailed_summary", "main_topics", "sentiment", "confidence_score"]
    
    def _get_default_value(self, field: str) -> Any:
        """Get default value for a field."""
        defaults = {
            "executive_summary": "Content summary",
            "key_points": [],
            "detailed_summary": "Content summarization completed",
            "main_topics": [],
            "sentiment": "neutral",
            "confidence_score": 0.5
        }
        return defaults.get(field, None)
    
    def _create_result(self, validated_data: Dict[str, Any], confidence_score: float, query: ParsedQuery) -> ContentSummary:
        """Create the final ContentSummary result from validated data."""
        validated_data['confidence_score'] = confidence_score
        return ContentSummary(**validated_data)
    
    def _get_fallback_data(self, query: ParsedQuery, error_message: str) -> Dict[str, Any]:
        """Get fallback data for validation failures."""
        return {
            "executive_summary": f"Content related to {query.base_result.query_text}",
            "key_points": [f"Content covers {query.base_result.query_text} topics"],
            "detailed_summary": f"This content appears to be related to {query.base_result.query_text}. Error: {error_message}",
            "main_topics": [query.base_result.query_text],
            "sentiment": "neutral",
            "confidence_score": 0.3
        }
    
    def create_fallback_response(self, query: ParsedQuery, error_message: str) -> ContentSummary:
        """Create fallback content summary when processing fails."""
        return ContentSummary(
            executive_summary=f"Content related to {query.base_result.query_text}",
            key_points=[f"Content covers {query.base_result.query_text} topics"],
            detailed_summary=f"This content appears to be related to {query.base_result.query_text}. Summarization unavailable due to error: {error_message}",
            main_topics=[query.base_result.query_text],
            sentiment="neutral",
            confidence_score=0.1,
            processing_metadata={
                "method": "fallback",
                "error": error_message,
                "fallback_reason": "Summarization failed, using minimal summary"
            }
        )
    
    def _validate_summary_length(self, summary: ContentSummary, max_length: int) -> ContentSummary:
        """Validate and truncate summary if it exceeds maximum length."""
        if len(summary.detailed_summary) <= max_length:
            return summary
        
        # Truncate detailed summary
        truncated_summary = summary.detailed_summary[:max_length-3] + "..."
        summary.detailed_summary = truncated_summary
        
        # Reduce confidence score due to truncation
        summary.confidence_score = max(0.1, summary.confidence_score * 0.8)
        
        # Add truncation metadata
        if not hasattr(summary, 'processing_metadata'):
            summary.processing_metadata = {}
        summary.processing_metadata['truncated'] = True
        summary.processing_metadata['original_length'] = len(summary.detailed_summary)
        summary.processing_metadata['truncated_length'] = max_length
        
        return summary
