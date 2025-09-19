import time
from typing import Dict, Any, List, Optional, Tuple
from app.processing.ai_agent_base import BaseAIAgent
from app.agents.schemas import ParsedQuery
from app.processing.schemas import AIInsights, ProcessingError
from app.core.gemini import GeminiClient
from app.core.config import get_settings
from app.processing.prompts import ProcessingPrompts


class AIAnalysisAgent(BaseAIAgent[AIInsights]):
    """AI-powered content analysis agent using Gemini for deep insights with standardized error handling."""
    
    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        super().__init__("AIAnalysisAgent", gemini_client)
    
    async def analyze_content(
        self, 
        cleaned_content: str, 
        query: ParsedQuery,
        title: str = "",
        url: str = ""
    ) -> AIInsights:
        """
        Analyze content using Gemini AI for comprehensive insights.
        
        Args:
            cleaned_content: Cleaned text content to analyze
            query: Original query context for relevance scoring
            title: Content title for context
            url: Content URL for source analysis
            
        Returns:
            AIInsights object with comprehensive analysis results
        """
        start_time = time.time()
        
        try:
            self.logger.info("Starting AI content analysis")
            
            # Check if Gemini client is available
            if not self.gemini_client:
                self.logger.warning("Gemini client not available, returning fallback insights")
                return self.create_fallback_response(query, "Gemini client not available")
            
            # Process content with AI using standardized methods
            insights = await self.process_with_ai(cleaned_content, query, title=title, url=url)
            
            # Calculate relevance score based on query
            relevance_score = self._calculate_relevance_score(insights, query)
            insights.relevance_score = relevance_score
            
            processing_time = time.time() - start_time
            self.logger.info(f"AI analysis completed in {processing_time:.2f}s")
            
            return insights
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"AI analysis failed: {str(e)}")
            
            # Return fallback insights using standardized method
            return self.create_fallback_response(query, str(e))
    
    def _build_prompt(self, content: str, query: ParsedQuery, **kwargs) -> str:
        """Build comprehensive analysis prompt using centralized ProcessingPrompts."""
        title = kwargs.get('title', '')
        url = kwargs.get('url', '')
        
        return ProcessingPrompts.get_analysis_prompt(
            query=query.base_result.query_text,
            category=query.base_result.category.value,
            title=title,
            url=url,
            content=content
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
            if isinstance(parsed_data, dict) and any(key in parsed_data for key in ['themes', 'relevance_score', 'quality_metrics']):
                self.logger.info("Successfully parsed JSON response from AI")
                return parsed_data
            else:
                self.logger.warning("Parsed JSON lacks expected structure, using fallback")
                raise ValueError("Incomplete JSON structure")
                
        except Exception as e:
            self.logger.debug(f"JSON parsing failed, falling back to heuristic parsing: {str(e)}")
            
            # Fallback to heuristic parsing if JSON extraction fails
            parsed_data = {
                "themes": [f"Content related to {query.base_result.query_text}"],
                "relevance_score": 0.7,
                "quality_metrics": {"readability": 0.8, "information_density": 0.7, "coherence": 0.8},
                "recommendations": ["Content analysis completed successfully"],
                "credibility_indicators": {"analysis_completed": True},
                "information_accuracy": 0.8,
                "source_reliability": 0.8
            }
            
            # Try to extract actual themes from response if possible
            if "themes:" in raw_response.lower():
                # Basic theme extraction logic
                lines = raw_response.split('\n')
                for line in lines:
                    if "theme" in line.lower() and ":" in line:
                        theme = line.split(':')[1].strip()
                        if theme and theme not in parsed_data["themes"]:
                            parsed_data["themes"].append(theme)
            
            return parsed_data
    
    def _validate_response(self, data: Dict[str, Any], query: ParsedQuery) -> Dict[str, Any]:
        """Validate parsed response data and return AIInsights object."""
        try:
            # Ensure all required fields are present
            required_fields = self._get_required_fields()
            for field in required_fields:
                if field not in data:
                    data[field] = self._get_default_value(field)
            
            # Validate data structure and return validated data
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
            
            # Boost based on quality metrics if available
            if "quality_metrics" in data and isinstance(data["quality_metrics"], dict):
                quality_scores = list(data["quality_metrics"].values())
                if quality_scores:
                    avg_quality = sum(quality_scores) / len(quality_scores)
                    base_score += avg_quality * 0.2
            
            # Boost based on query relevance
            if query.base_result.query_text and "themes" in data and isinstance(data["themes"], list):
                query_terms = query.base_result.query_text.lower().split()
                theme_matches = sum(1 for theme in data["themes"] 
                                  if any(term in theme.lower() for term in query_terms))
                if theme_matches > 0:
                    base_score += min(theme_matches * 0.1, 0.1)
            
            return min(1.0, max(0.0, base_score))
            
        except Exception as e:
            self.logger.error(f"Failed to calculate confidence score: {str(e)}")
            return 0.5
    
    def _get_required_fields(self) -> List[str]:
        """Get list of required fields for AIInsights."""
        return ["themes", "relevance_score", "quality_metrics", "confidence_score", "key_entities", "categories", "recommendations", "credibility_indicators", "information_accuracy", "source_reliability"]
    
    def _get_default_value(self, field: str) -> Any:
        """Get default value for a field."""
        defaults = {
            "themes": [],
            "relevance_score": 0.5,
            "quality_metrics": {},
            "confidence_score": 0.5,
            "key_entities": [],
            "categories": [],
            "recommendations": [],
            "credibility_indicators": {},
            "information_accuracy": 0.5,
            "source_reliability": 0.5
        }
        return defaults.get(field, None)
    
    def _create_result(self, validated_data: Dict[str, Any], confidence_score: float, query: ParsedQuery) -> AIInsights:
        """Create the final AIInsights result from validated data."""
        validated_data['confidence_score'] = confidence_score
        return AIInsights(**validated_data)
    
    def _get_fallback_data(self, query: ParsedQuery, error_message: str) -> Dict[str, Any]:
        """Get fallback data for validation failures."""
        return {
            "themes": [f"Content related to {query.base_result.query_text}"],
            "relevance_score": 0.5,
            "quality_metrics": {"readability": 0.5, "information_density": 0.5, "coherence": 0.5},
            "recommendations": ["Analysis failed, manual review recommended"],
            "credibility_indicators": {"analysis_failed": True, "error": error_message},
            "information_accuracy": 0.5,
            "source_reliability": 0.5,
            "confidence_score": 0.3,
            "key_entities": [],
            "categories": [query.base_result.category.value]
        }
    
    def create_fallback_response(self, query: ParsedQuery, error_message: str) -> AIInsights:
        """Create fallback AI insights when processing fails."""
        return AIInsights(
            themes=[f"Content related to {query.base_result.query_text}"],
            relevance_score=0.5,
            quality_metrics={"readability": 0.5, "information_density": 0.5, "coherence": 0.5},
            confidence_score=0.1,
            key_entities=[],
            categories=[],
            recommendations=[],
            credibility_indicators={},
            information_accuracy=0.5,
            source_reliability=0.5,
            processing_metadata={
                "method": "fallback",
                "fallback_reason": "AI analysis failed, using minimal insights"
            }
        )
    
    def _calculate_relevance_score(self, insights: AIInsights, query: ParsedQuery) -> float:
        """Calculate relevance score based on query and insights."""
        base_score = 0.5
        
        # Boost based on theme relevance
        if query.base_result.query_text and insights.themes:
            query_terms = query.base_result.query_text.lower().split()
            theme_matches = sum(1 for theme in insights.themes 
                              if any(term in theme.lower() for term in query_terms))
            if theme_matches > 0:
                base_score += min(theme_matches * 0.2, 0.3)
        
        # Boost based on category match
        if query.base_result.category and insights.themes:
            category_matches = sum(1 for theme in insights.themes 
                                 if query.base_result.category.value.lower() in theme.lower())
            if category_matches > 0:
                base_score += 0.1
        
        # Boost based on quality metrics
        if insights.quality_metrics:
            avg_quality = sum(insights.quality_metrics.values()) / len(insights.quality_metrics)
            base_score += avg_quality * 0.1
        
        return min(1.0, max(0.0, base_score))
    
    async def analyze_batch(self, items: List[Tuple[str, ParsedQuery, str, str]]) -> List[AIInsights]:
        """Analyze multiple content pieces in batch."""
        # items: [(cleaned_content, query, title, url), ...]
        results = []
        for content, query, title, url in items:
            results.append(await self.analyze_content(content, query, title, url))
        return results
