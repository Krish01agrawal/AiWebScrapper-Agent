import time
import json
import re
from typing import Dict, Any, List, Optional
from app.agents.base import BaseAgent
from app.agents.schemas import ParsedQuery
from app.processing.schemas import StructuredData, ProcessingError
from app.core.gemini import GeminiClient
from app.core.config import get_settings
from app.processing.prompts import ProcessingPrompts


class StructuredDataExtractor(BaseAgent):
    """Structured data extraction agent for extracting key information using Gemini."""
    
    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        super().__init__(name="StructuredDataExtractor", description="Extracts structured data from content using AI")
        
        # Accept injected client and set to None if absent, logging a clear warning
        if gemini_client:
            self.gemini_client = gemini_client
            self.logger.info("StructuredDataExtractor initialized with injected Gemini client")
        else:
            self.gemini_client = None
            self.logger.warning("StructuredDataExtractor initialized without Gemini client - AI features will be disabled")
    
    async def extract_structured_data(
        self, 
        content: str, 
        query: Optional[ParsedQuery] = None,
        title: str = "",
        url: str = ""
    ) -> StructuredData:
        """
        Extract structured data from content using Gemini AI.
        
        Args:
            content: Content to extract data from
            query: Original query context for domain-specific extraction
            title: Content title for context
            url: Content URL for source analysis
            
        Returns:
            StructuredData object with extracted information
        """
        start_time = time.time()
        
        try:
            self.logger.info("Starting structured data extraction")
            
            # Create default query if none provided
            if query is None:
                from app.agents.schemas import ParsedQuery, BaseQueryResult, QueryCategory
                query = ParsedQuery(base_result=BaseQueryResult(
                    query_text="general", confidence_score=1.0, processing_time=0.0, category=QueryCategory.GENERAL
                ))
            
            # Check if Gemini client is available
            if not self.gemini_client:
                self.logger.warning("Gemini client not available, returning fallback structured data")
                return self._create_fallback_structured_data(query, "Gemini client not available")
            
            # Build extraction prompt based on query category
            extraction_prompt = self._build_extraction_prompt(content, query, title, url)
            
            # Get AI extraction from Gemini
            ai_response = await self._get_ai_extraction(extraction_prompt)
            
            # Parse and validate AI response
            structured_data = self._parse_extraction_response(ai_response, query)
            
            # Enhance with pattern-based extraction
            enhanced_data = await self._enhance_with_patterns(structured_data, content, query)
            
            # Validate and normalize extracted data
            validated_data = self._validate_extracted_data(enhanced_data)
            
            processing_time = time.time() - start_time
            self.logger.info(f"Structured data extraction completed in {processing_time:.2f}s")
            
            return validated_data
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Structured data extraction failed: {str(e)}")
            
            # Return fallback structured data
            return self._create_fallback_structured_data(query, str(e))
    
    def _build_extraction_prompt(
        self, 
        content: str, 
        query: ParsedQuery, 
        title: str, 
        url: str
    ) -> str:
        """Build domain-specific extraction prompt for Gemini."""
        
        # Get extraction prompt from ProcessingPrompts
        extraction_prompt = ProcessingPrompts.get_extraction_prompt(
            query=query.base_result.query_text,
            category=query.base_result.category.value,
            title=title,
            url=url,
            content=content[:3500],  # Limit content length for API efficiency
            focus="key information",
            entities="entities and concepts",
            key_values="key data points"
        )
        
        return extraction_prompt
    
    async def _get_ai_extraction(self, prompt: str) -> str:
        """Get AI extraction from Gemini client."""
        # Add null check for Gemini client
        if not self.gemini_client:
            raise RuntimeError("Gemini client not available for AI extraction")
        
        try:
            response = await self.gemini_client.generate_content(
                prompt,
                generation_config={"temperature": 0.1, "max_output_tokens": 2000}
            )
            raw_text = getattr(response, "text", str(response))
            return raw_text
        except Exception as e:
            self.logger.error(f"Gemini API call failed: {str(e)}")
            raise
    
    def _parse_extraction_response(self, ai_response: str, query: ParsedQuery) -> StructuredData:
        """Parse and validate AI response into StructuredData object with comprehensive error handling."""
        try:
            # First try to find fenced JSON blocks
            json_block_match = re.search(r'```json\s*(.*?)\s*```', ai_response, re.DOTALL)
            if json_block_match:
                json_str = json_block_match.group(1).strip()
                parsed_data = json.loads(json_str)
            else:
                # Try to find JSON object with proper brace matching
                json_start = ai_response.find('{')
                if json_start == -1:
                    raise ValueError("No JSON found in AI response")
                
                # Find matching closing brace using stack-based approach
                brace_count = 0
                json_end = -1
                
                for i, char in enumerate(ai_response[json_start:], json_start):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                if json_end == -1:
                    raise ValueError("Incomplete JSON object in AI response")
                
                json_str = ai_response[json_start:json_end]
                parsed_data = json.loads(json_str)
            
            # Create StructuredData object with parsed data - wrap in try-catch for Pydantic validation
            try:
                structured_data = StructuredData(
                    entities=parsed_data.get("entities", []),
                    key_value_pairs=parsed_data.get("key_value_pairs", {}),
                    categories=parsed_data.get("categories", []),
                    confidence_scores=parsed_data.get("confidence_scores", {}),
                    tables=parsed_data.get("tables", []),
                    measurements=parsed_data.get("measurements", [])
                )
                return structured_data
                
            except Exception as validation_error:
                # Handle Pydantic validation errors specifically
                self.logger.error(f"Pydantic validation failed for StructuredData: {str(validation_error)}")
                # Try to create with sanitized data
                try:
                    # Sanitize and validate individual fields
                    entities = parsed_data.get("entities", [])
                    if not isinstance(entities, list):
                        entities = [str(entities)] if entities else []
                    
                    key_value_pairs = parsed_data.get("key_value_pairs", {})
                    if not isinstance(key_value_pairs, dict):
                        key_value_pairs = {"extraction_failed": True}
                    
                    categories = parsed_data.get("categories", [])
                    if not isinstance(categories, list):
                        categories = [str(categories)] if categories else [query.base_result.category.value]
                    
                    confidence_scores = parsed_data.get("confidence_scores", {})
                    if not isinstance(confidence_scores, dict):
                        confidence_scores = {"extraction_failed": 0.1}
                    else:
                        # Validate confidence score values
                        for key in confidence_scores:
                            try:
                                score = float(confidence_scores[key])
                                confidence_scores[key] = max(0.0, min(1.0, score))
                            except (ValueError, TypeError):
                                confidence_scores[key] = 0.5
                    
                    tables = parsed_data.get("tables", [])
                    if not isinstance(tables, list):
                        tables = []
                    
                    measurements = parsed_data.get("measurements", [])
                    if not isinstance(measurements, list):
                        measurements = []
                    
                    structured_data = StructuredData(
                        entities=entities,
                        key_value_pairs=key_value_pairs,
                        categories=categories,
                        confidence_scores=confidence_scores,
                        tables=tables,
                        measurements=measurements
                    )
                    return structured_data
                    
                except Exception as fallback_error:
                    self.logger.error(f"Fallback StructuredData creation also failed: {str(fallback_error)}")
                    return self._create_fallback_structured_data(query, f"Extraction response validation failed: {str(validation_error)}")
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.warning(f"Failed to parse extraction response: {str(e)}")
            return self._create_fallback_structured_data(query, f"Extraction response parsing failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error in extraction response parsing: {str(e)}")
            return self._create_fallback_structured_data(query, f"Extraction response parsing failed: {str(e)}")
    
    async def _enhance_with_patterns(
        self, 
        structured_data: StructuredData, 
        content: str, 
        query: ParsedQuery
    ) -> StructuredData:
        """Enhance extracted data with pattern-based extraction."""
        enhanced = structured_data
        
        # Extract email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content)
        if emails:
            enhanced.key_value_pairs["emails"] = list(set(emails))
            enhanced.confidence_scores["emails"] = 0.99
        
        # Extract phone numbers
        phone_pattern = r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, content)
        if phones:
            enhanced.key_value_pairs["phone_numbers"] = list(set(phones))
            enhanced.confidence_scores["phone_numbers"] = 0.95
        
        # Extract URLs
        url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
        urls = re.findall(url_pattern, content)
        if urls:
            enhanced.key_value_pairs["urls"] = list(set(urls))
            enhanced.confidence_scores["urls"] = 0.98
        
        # Extract dates
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YYYY
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',  # YYYY/MM/DD
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'  # Month DD, YYYY
        ]
        
        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, content, re.IGNORECASE))
        
        if dates:
            enhanced.key_value_pairs["dates"] = list(set(dates))
            enhanced.confidence_scores["dates"] = 0.9
        
        # Extract prices
        price_pattern = r'\$[\d,]+(?:\.\d{2})?'
        prices = re.findall(price_pattern, content)
        if prices:
            enhanced.key_value_pairs["prices"] = list(set(prices))
            enhanced.confidence_scores["prices"] = 0.95
        
        # Extract percentages
        percentage_pattern = r'\d+(?:\.\d+)?%'
        percentages = re.findall(percentage_pattern, content)
        if percentages:
            enhanced.key_value_pairs["percentages"] = list(set(percentages))
            enhanced.confidence_scores["percentages"] = 0.95
        
        return enhanced
    
    def _validate_extracted_data(self, structured_data: StructuredData) -> StructuredData:
        """Validate and normalize extracted data."""
        validated = structured_data
        
        # Validate confidence scores
        for key in validated.confidence_scores:
            score = validated.confidence_scores[key]
            if not isinstance(score, (int, float)) or score < 0 or score > 1:
                validated.confidence_scores[key] = 0.5
        
        # Validate entities
        for entity in validated.entities:
            if not isinstance(entity, dict):
                continue
            
            # Ensure required fields
            if "name" not in entity:
                entity["name"] = "Unknown"
            
            if "type" not in entity:
                entity["type"] = "concept"
            
            # Validate properties
            if "properties" not in entity:
                entity["properties"] = {}
            
            if "confidence" not in entity["properties"]:
                entity["properties"]["confidence"] = 0.5
        
        # Validate categories
        validated.categories = [cat for cat in validated.categories if isinstance(cat, str) and cat.strip()]
        
        # Validate tables
        for table in validated.tables:
            if not isinstance(table, dict):
                continue
            
            if "headers" not in table:
                table["headers"] = []
            
            if "rows" not in table:
                table["rows"] = []
        
        return validated
    
    def _create_fallback_structured_data(self, query: ParsedQuery, error_message: str) -> StructuredData:
        """Create fallback structured data when extraction fails."""
        self.logger.warning(f"Creating fallback structured data due to: {error_message}")
        
        return StructuredData(
            entities=[],
            key_value_pairs={"extraction_error": error_message},
            categories=[query.base_result.category.value],
            confidence_scores={"extraction_error": 0.1},
            tables=[],
            measurements=[]
        )
    
    async def extract_batch(
        self, 
        contents: List[Dict[str, Any]], 
        query: ParsedQuery
    ) -> List[StructuredData]:
        """Extract structured data from multiple content pieces in batch."""
        self.logger.info(f"Starting batch extraction from {len(contents)} content pieces")
        
        extraction_list = []
        for i, content_data in enumerate(contents):
            try:
                structured_data = await self.extract_structured_data(
                    content=content_data.get("cleaned_content", ""),
                    query=query,
                    title=content_data.get("title", ""),
                    url=content_data.get("url", "")
                )
                extraction_list.append(structured_data)
                
                # Log progress
                if (i + 1) % 5 == 0:
                    self.logger.info(f"Batch extraction progress: {i + 1}/{len(contents)}")
                    
            except Exception as e:
                self.logger.error(f"Failed to extract from content {i}: {str(e)}")
                fallback_data = self._create_fallback_structured_data(query, str(e))
                extraction_list.append(fallback_data)
        
        self.logger.info(f"Batch extraction completed: {len(extraction_list)} extractions generated")
        return extraction_list
    
    async def extract_domain_specific(
        self, 
        content: str, 
        query: ParsedQuery,
        extraction_focus: str
    ) -> StructuredData:
        """
        Extract domain-specific data based on extraction focus.
        
        Args:
            content: Content to extract from
            query: Original query context
            extraction_focus: Specific focus area (e.g., "pricing", "features", "performance")
            
        Returns:
            Focused StructuredData object
        """
        try:
            self.logger.info(f"Extracting domain-specific data for focus: {extraction_focus}")
            
            # Build focused extraction prompt
            focused_prompt = self._build_focused_extraction_prompt(content, query, extraction_focus)
            
            # Get AI extraction
            ai_response = await self._get_ai_extraction(focused_prompt)
            
            # Parse response
            structured_data = self._parse_extraction_response(ai_response, query)
            
            # Add focus context
            structured_data.categories.insert(0, extraction_focus)
            
            return structured_data
            
        except Exception as e:
            self.logger.error(f"Domain-specific extraction failed: {str(e)}")
            return self._create_fallback_structured_data(query, f"Domain-specific extraction failed: {str(e)}")
    
    def _build_focused_extraction_prompt(
        self, 
        content: str, 
        query: ParsedQuery, 
        extraction_focus: str
    ) -> str:
        """Build focused extraction prompt."""
        from app.processing.prompts import ProcessingPrompts
        
        # Get base extraction prompt and customize for focus
        base_prompt = ProcessingPrompts.get_extraction_prompt(
            query=query.base_result.query_text,
            category=query.base_result.category.value,
            title="",
            url="",
            content=content[:2500],
            focus=extraction_focus,
            entities=f"{extraction_focus} related entities",
            key_values=f"{extraction_focus} related data"
        )
        
        # Add focus-specific instructions
        focus_instructions = f"""
        
        IMPORTANT: Focus EXCLUSIVELY on {extraction_focus} information. Do not extract other types of data.
        Only return data that is directly related to {extraction_focus}.
        """
        
        return base_prompt + focus_instructions
    
    async def execute(self, content: str, query: Optional[ParsedQuery] = None, title: str = "", url: str = "", **kwargs) -> StructuredData:
        """Execute the agent's main functionality."""
        return await self.extract_structured_data(content, query, title, url)
