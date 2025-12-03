import time
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from app.core.config import get_settings


class PromptType(Enum):
    """Enumeration of prompt types for categorization."""
    CONTENT_ANALYSIS = "content_analysis"
    SUMMARIZATION = "summarization"
    EXTRACTION = "extraction"
    DUPLICATE_DETECTION = "duplicate_detection"
    CLEANING = "cleaning"


class PromptVersion:
    """Represents a version of a prompt template."""
    
    def __init__(self, version_id: str, template: str, prompt_type: PromptType, 
                 metadata: Optional[Dict[str, Any]] = None):
        self.version_id = version_id
        self.template = template
        self.prompt_type = prompt_type
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.is_active = True
        self.usage_count = 0
        self.success_count = 0
        self.avg_response_time = 0.0
        self.avg_confidence_score = 0.0
        self.ab_test_weight = 1.0  # For A/B testing
    
    def update_metrics(self, success: bool, response_time: float, confidence_score: float = 0.0):
        """Update prompt performance metrics."""
        self.usage_count += 1
        
        if success:
            self.success_count += 1
        
        # Update average response time
        if self.usage_count == 1:
            self.avg_response_time = response_time
        else:
            self.avg_response_time = (
                (self.avg_response_time * (self.usage_count - 1) + response_time) / self.usage_count
            )
        
        # Update average confidence score
        if confidence_score > 0:
            if self.usage_count == 1:
                self.avg_confidence_score = confidence_score
            else:
                self.avg_confidence_score = (
                    (self.avg_confidence_score * (self.usage_count - 1) + confidence_score) / self.usage_count
                )
    
    def get_success_rate(self) -> float:
        """Calculate success rate."""
        return self.success_count / self.usage_count if self.usage_count > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'version_id': self.version_id,
            'template': self.template,
            'prompt_type': self.prompt_type.value,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'success_count': self.success_count,
            'avg_response_time': self.avg_response_time,
            'avg_confidence_score': self.avg_confidence_score,
            'ab_test_weight': self.ab_test_weight
        }


class PromptEffectivenessTracker:
    """Tracks prompt effectiveness and performance metrics."""
    
    def __init__(self):
        self.prompt_versions: Dict[str, PromptVersion] = {}
        self.performance_history: List[Dict[str, Any]] = []
        self.ab_test_results: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_prompt_version(self, prompt_version: PromptVersion):
        """Register a new prompt version."""
        self.prompt_versions[prompt_version.version_id] = prompt_version
        self.logger.info(f"Registered prompt version: {prompt_version.version_id}")
    
    def record_usage(self, version_id: str, success: bool, response_time: float, 
                    confidence_score: float = 0.0, content_characteristics: Optional[Dict[str, Any]] = None):
        """Record usage of a prompt version."""
        if version_id not in self.prompt_versions:
            self.logger.warning(f"Unknown prompt version: {version_id}")
            return
        
        prompt_version = self.prompt_versions[version_id]
        prompt_version.update_metrics(success, response_time, confidence_score)
        
        # Record performance history
        performance_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'version_id': version_id,
            'prompt_type': prompt_version.prompt_type.value,
            'success': success,
            'response_time': response_time,
            'confidence_score': confidence_score,
            'content_characteristics': content_characteristics or {}
        }
        self.performance_history.append(performance_record)
        
        # Keep only recent history (last 1000 records)
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]
    
    def get_best_performing_version(self, prompt_type: PromptType, 
                                  content_characteristics: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Get the best performing prompt version for a given type and content characteristics."""
        relevant_versions = [
            v for v in self.prompt_versions.values()
            if v.prompt_type == prompt_type and v.is_active and v.usage_count >= 5
        ]
        
        if not relevant_versions:
            return None
        
        # Score versions based on multiple factors
        scored_versions = []
        for version in relevant_versions:
            score = self._calculate_version_score(version, content_characteristics)
            scored_versions.append((version.version_id, score))
        
        # Return the highest scoring version
        scored_versions.sort(key=lambda x: x[1], reverse=True)
        return scored_versions[0][0] if scored_versions else None
    
    def _calculate_version_score(self, version: PromptVersion, 
                               content_characteristics: Optional[Dict[str, Any]]) -> float:
        """Calculate a score for a prompt version based on performance and content fit."""
        # Base score from success rate and confidence
        base_score = (version.get_success_rate() * 0.6 + 
                     version.avg_confidence_score * 0.4)
        
        # Bonus for recent usage (recency bias)
        days_since_creation = (datetime.utcnow() - version.created_at).days
        recency_bonus = max(0, 1.0 - (days_since_creation / 30)) * 0.1
        
        # Bonus for content characteristics match
        content_bonus = 0.0
        if content_characteristics and version.metadata.get('content_characteristics'):
            match_score = self._calculate_content_match_score(
                content_characteristics, 
                version.metadata['content_characteristics']
            )
            content_bonus = match_score * 0.2
        
        return min(1.0, base_score + recency_bonus + content_bonus)
    
    def _calculate_content_match_score(self, actual: Dict[str, Any], 
                                     expected: Dict[str, Any]) -> float:
        """Calculate how well content characteristics match expected patterns."""
        if not actual or not expected:
            return 0.0
        
        matches = 0
        total = 0
        
        for key, expected_value in expected.items():
            if key in actual:
                total += 1
                if isinstance(expected_value, (int, float)):
                    # Numeric range matching
                    if isinstance(actual[key], (int, float)):
                        tolerance = expected_value * 0.2  # 20% tolerance
                        if abs(actual[key] - expected_value) <= tolerance:
                            matches += 1
                elif isinstance(expected_value, str):
                    # String matching
                    if expected_value.lower() in actual[key].lower():
                        matches += 1
                elif isinstance(expected_value, list):
                    # List matching
                    if any(item in actual[key] for item in expected_value):
                        matches += 1
        
        return matches / total if total > 0 else 0.0
    
    def start_ab_test(self, prompt_type: PromptType, version_ids: List[str], 
                     weights: Optional[List[float]] = None):
        """Start an A/B test for prompt versions."""
        if len(version_ids) < 2:
            self.logger.warning("A/B test requires at least 2 versions")
            return
        
        # Normalize weights
        if weights is None:
            weights = [1.0] * len(version_ids)
        
        if len(weights) != len(version_ids):
            self.logger.warning("Weights count must match version count")
            return
        
        # Normalize weights to sum to 1.0
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        
        # Set A/B test weights
        for version_id, weight in zip(version_ids, normalized_weights):
            if version_id in self.prompt_versions:
                self.prompt_versions[version_id].ab_test_weight = weight
        
        test_id = f"ab_test_{prompt_type.value}_{int(time.time())}"
        self.ab_test_results[test_id] = {
            'prompt_type': prompt_type.value,
            'version_ids': version_ids,
            'weights': normalized_weights,
            'start_time': datetime.utcnow().isoformat(),
            'results': {vid: {'usage': 0, 'success': 0} for vid in version_ids}
        }
        
        self.logger.info(f"Started A/B test {test_id} for {prompt_type.value}")
    
    def select_version_for_ab_test(self, prompt_type: PromptType) -> Optional[str]:
        """Select a prompt version for A/B testing based on weights."""
        relevant_versions = [
            v for v in self.prompt_versions.values()
            if v.prompt_type == prompt_type and v.is_active and v.ab_test_weight > 0
        ]
        
        if not relevant_versions:
            return None
        
        # Weighted random selection
        import random
        total_weight = sum(v.ab_test_weight for v in relevant_versions)
        if total_weight <= 0:
            return None
        
        rand_val = random.uniform(0, total_weight)
        current_weight = 0
        
        for version in relevant_versions:
            current_weight += version.ab_test_weight
            if rand_val <= current_weight:
                return version.version_id
        
        return relevant_versions[-1].version_id
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of prompt performance across all versions."""
        summary = {
            'total_versions': len(self.prompt_versions),
            'active_versions': sum(1 for v in self.prompt_versions.values() if v.is_active),
            'total_usage': sum(v.usage_count for v in self.prompt_versions.values()),
            'overall_success_rate': 0.0,
            'by_type': {}
        }
        
        # Calculate overall success rate
        total_success = sum(v.success_count for v in self.prompt_versions.values())
        total_usage = sum(v.usage_count for v in self.prompt_versions.values())
        if total_usage > 0:
            summary['overall_success_rate'] = total_success / total_usage
        
        # Group by prompt type
        for prompt_type in PromptType:
            type_versions = [v for v in self.prompt_versions.values() 
                           if v.prompt_type == prompt_type]
            if type_versions:
                type_usage = sum(v.usage_count for v in type_versions)
                type_success = sum(v.success_count for v in type_versions)
                type_success_rate = type_success / type_usage if type_usage > 0 else 0.0
                
                summary['by_type'][prompt_type.value] = {
                    'version_count': len(type_versions),
                    'usage_count': type_usage,
                    'success_rate': type_success_rate,
                    'avg_response_time': sum(v.avg_response_time for v in type_versions) / len(type_versions)
                }
        
        return summary


class ProcessingPrompts:
    """Specialized prompts for the processing pipeline with versioning, A/B testing, and effectiveness tracking."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self.effectiveness_tracker = PromptEffectivenessTracker()
        self._initialize_prompt_versions()
        self._validate_prompt_templates()
    
    def _initialize_prompt_versions(self):
        """Initialize prompt versions with the effectiveness tracker."""
        # Create initial versions for each prompt type
        self._create_initial_versions()
        
        # Start A/B tests if multiple versions exist
        self._setup_ab_tests()
    
    def _create_initial_versions(self):
        """Create initial prompt versions for each type."""
        # Content Analysis versions
        self._register_content_analysis_versions()
        
        # Summarization versions
        self._register_summarization_versions()
        
        # Extraction versions
        self._register_extraction_versions()
        
        # Duplicate Detection versions
        self._register_duplicate_detection_versions()
    
    def _register_content_analysis_versions(self):
        """Register different versions of content analysis prompts."""
        # Version 1: Standard analysis
        v1 = PromptVersion(
            version_id="content_analysis_v1",
            template=self.CONTENT_ANALYSIS_BASE,
            prompt_type=PromptType.CONTENT_ANALYSIS,
            metadata={
                'description': 'Standard content analysis prompt',
                'content_characteristics': {
                    'content_length': [100, 10000],
                    'content_type': ['article', 'review', 'guide', 'news', 'tutorial']
                }
            }
        )
        self.effectiveness_tracker.register_prompt_version(v1)
        
        # Version 2: Focused analysis
        v2 = PromptVersion(
            version_id="content_analysis_v2",
            template=self.CONTENT_ANALYSIS_FOCUSED,
            prompt_type=PromptType.CONTENT_ANALYSIS,
            metadata={
                'description': 'Focused content analysis with specific insights',
                'content_characteristics': {
                    'content_length': [500, 5000],
                    'content_type': ['article', 'guide']
                }
            }
        )
        self.effectiveness_tracker.register_prompt_version(v2)
    
    def _register_summarization_versions(self):
        """Register different versions of summarization prompts."""
        # Version 1: Standard summarization
        v1 = PromptVersion(
            version_id="summarization_v1",
            template=self.SUMMARIZATION_BASE,
            prompt_type=PromptType.SUMMARIZATION,
            metadata={
                'description': 'Standard summarization prompt',
                'content_characteristics': {
                    'content_length': [200, 8000],
                    'summary_length': [100, 1000]
                }
            }
        )
        self.effectiveness_tracker.register_prompt_version(v1)
        
        # Version 2: Executive summary focus
        v2 = PromptVersion(
            version_id="summarization_v2",
            template=self.SUMMARIZATION_EXECUTIVE,
            prompt_type=PromptType.SUMMARIZATION,
            metadata={
                'description': 'Executive summary focused prompt',
                'content_characteristics': {
                    'content_length': [1000, 15000],
                    'summary_length': [200, 500]
                }
            }
        )
        self.effectiveness_tracker.register_prompt_version(v2)
    
    def _register_extraction_versions(self):
        """Register different versions of extraction prompts."""
        # Version 1: Standard extraction
        v1 = PromptVersion(
            version_id="extraction_v1",
            template=self.EXTRACTION_BASE,
            prompt_type=PromptType.EXTRACTION,
            metadata={
                'description': 'Standard structured data extraction',
                'content_characteristics': {
                    'content_length': [100, 5000],
                    'content_type': ['product', 'article', 'review']
                }
            }
        )
        self.effectiveness_tracker.register_prompt_version(v1)
    
    def _register_duplicate_detection_versions(self):
        """Register different versions of duplicate detection prompts."""
        # Version 1: Standard duplicate detection
        v1 = PromptVersion(
            version_id="duplicate_detection_v1",
            template=self.DUPLICATE_DETECTION,
            prompt_type=PromptType.DUPLICATE_DETECTION,
            metadata={
                'description': 'Standard duplicate detection prompt',
                'content_characteristics': {
                    'content_length': [100, 3000],
                    'content_type': ['article', 'review', 'guide']
                }
            }
        )
        self.effectiveness_tracker.register_prompt_version(v1)
    
    def _setup_ab_tests(self):
        """Setup A/B tests for different prompt types."""
        # A/B test for content analysis
        content_analysis_versions = [
            v.version_id for v in self.effectiveness_tracker.prompt_versions.values()
            if v.prompt_type == PromptType.CONTENT_ANALYSIS
        ]
        if len(content_analysis_versions) >= 2:
            self.effectiveness_tracker.start_ab_test(
                PromptType.CONTENT_ANALYSIS, 
                content_analysis_versions,
                weights=[0.5, 0.5]
            )
        
        # A/B test for summarization
        summarization_versions = [
            v.version_id for v in self.effectiveness_tracker.prompt_versions.values()
            if v.prompt_type == PromptType.SUMMARIZATION
        ]
        if len(summarization_versions) >= 2:
            self.effectiveness_tracker.start_ab_test(
                PromptType.SUMMARIZATION, 
                summarization_versions,
                weights=[0.6, 0.4]  # Slightly favor v1
            )
    
    def get_prompt(self, prompt_type: PromptType, content_characteristics: Optional[Dict[str, Any]] = None,
                   use_ab_testing: bool = True) -> Tuple[str, str]:
        """Get the best performing prompt for a given type and content characteristics."""
        if use_ab_testing:
            # Use A/B testing selection
            version_id = self.effectiveness_tracker.select_version_for_ab_test(prompt_type)
        else:
            # Use best performing version
            version_id = self.effectiveness_tracker.get_best_performing_version(
                prompt_type, content_characteristics
            )
        
        if not version_id:
            # Fallback to first available version
            available_versions = [
                v for v in self.effectiveness_tracker.prompt_versions.values()
                if v.prompt_type == prompt_type and v.is_active
            ]
            if available_versions:
                version_id = available_versions[0].version_id
            else:
                raise ValueError(f"No available prompt versions for type: {prompt_type}")
        
        prompt_version = self.effectiveness_tracker.prompt_versions[version_id]
        return prompt_version.template, version_id
    
    def record_prompt_performance(self, version_id: str, success: bool, response_time: float,
                                confidence_score: float = 0.0, content_characteristics: Optional[Dict[str, Any]] = None):
        """Record the performance of a prompt version."""
        self.effectiveness_tracker.record_usage(
            version_id, success, response_time, confidence_score, content_characteristics
        )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of prompt performance."""
        return self.effectiveness_tracker.get_performance_summary()
    
    def create_custom_prompt_version(self, prompt_type: PromptType, template: str, 
                                   metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a custom prompt version."""
        version_id = f"{prompt_type.value}_custom_{int(time.time())}"
        
        prompt_version = PromptVersion(
            version_id=version_id,
            template=template,
            prompt_type=prompt_type,
            metadata=metadata or {}
        )
        
        self.effectiveness_tracker.register_prompt_version(prompt_version)
        self.logger.info(f"Created custom prompt version: {version_id}")
        
        return version_id
    
    def _validate_prompt_templates(self):
        """Validate that all prompt templates have required variables."""
        required_variables = {
            "CONTENT_ANALYSIS_BASE": ["query", "category", "title", "url", "content"],
            "SUMMARIZATION_BASE": ["query", "category", "title", "content", "max_length"],
            "EXTRACTION_BASE": ["query", "category", "title", "url", "content", "focus", "entities", "key_values"],
            "DUPLICATE_DETECTION": ["title1", "content1", "title2", "content2"]
        }
        
        for template_name, required_vars in required_variables.items():
            template = getattr(self, template_name, None)
            if template:
                for var in required_vars:
                    if "{" + var + "}" not in template:
                        self.logger.warning(f"Template {template_name} missing required variable: {var}")
    
    def _get_configurable_limit(self, limit_type: str, default: int) -> int:
        """Get configurable limit from settings or use default."""
        try:
            if limit_type == "summary_length":
                return getattr(self.settings, 'processing_max_summary_length', default)
            elif limit_type == "similarity_content":
                return getattr(self.settings, 'gemini_max_similarity_content_length', default)
            elif limit_type == "extraction_content":
                return getattr(self.settings, 'gemini_max_content_length', default)
            else:
                return default
        except Exception:
            return default
    
    def _validate_input(self, **kwargs) -> None:
        """Validate input parameters for prompt generation."""
        for key, value in kwargs.items():
            if value is None:
                raise ValueError(f"Required parameter '{key}' cannot be None")
            if isinstance(value, str) and len(value.strip()) == 0:
                raise ValueError(f"Required parameter '{key}' cannot be empty")
    
    # Content Analysis Prompts
    CONTENT_ANALYSIS_BASE = """
    Analyze the following content and provide comprehensive insights. Focus on the query context: "{query}" (Category: {category}).

    Content Title: {title}
    Content URL: {url}
    
    Content:
    {content}
    
    Please provide analysis in the following JSON format, wrapped in fenced JSON blocks:

```json
{{
        "themes": ["theme1", "theme2", "theme3"],
        "quality_metrics": {{
            "readability": 0.75,
            "information_density": 0.82,
            "coherence": 0.91
        }},
        "recommendations": [
            "actionable recommendation 1",
            "actionable recommendation 2"
        ],
        "credibility_indicators": {{
            "expert_citations": 3,
            "recent_sources": true,
            "peer_reviewed": false,
            "author_credentials": "expert",
            "source_reputation": "high"
        }},
        "information_accuracy": 0.88,
        "source_reliability": 0.85,
        "key_entities": [
            {{
                "type": "person|organization|product|technology|concept",
                "name": "entity name",
                "relevance": 0.9,
                "description": "brief description"
            }}
        ],
        "content_type": "article|review|guide|news|tutorial",
        "target_audience": "beginner|intermediate|expert",
        "actionability_score": 0.8
    }}
```
    
    Focus on providing insights that would be valuable for someone searching for "{query}". Be specific and actionable.
    """
    
    CONTENT_ANALYSIS_FOCUSED = """
    Provide focused analysis of this content for the query: "{query}" (Category: {category}).

    Content Title: {title}
    Content URL: {url}
    
    Content:
    {content}
    
    Please provide focused analysis in JSON format, wrapped in fenced JSON blocks:

```json
{{
        "themes": ["theme1", "theme2"],
        "quality_metrics": {{
            "readability": 0.8,
            "information_density": 0.7,
            "coherence": 0.9
        }},
        "key_insights": ["insight1", "insight2"],
        "actionable_recommendations": ["recommendation1", "recommendation2"],
        "credibility_score": 0.85,
        "relevance_score": 0.9
    }}
```
    
    Focus on the most important aspects relevant to "{query}".
    """
    
    CONTENT_ANALYSIS_AI_TOOLS = """
    Analyze this AI tool content focusing on technical specifications, features, pricing, and use cases.

    Content:
    {content}
    
    Provide analysis in JSON format, wrapped in fenced JSON blocks:

```json
{{
        "themes": ["AI Technology", "Tool Features", "Use Cases"],
        "quality_metrics": {{
            "technical_depth": 0.8,
            "feature_coverage": 0.9,
            "pricing_clarity": 0.7
        }},
        "recommendations": [
            "Consider this tool for {specific_use_case}",
            "Evaluate pricing against alternatives"
        ],
        "credibility_indicators": {{
            "technical_accuracy": "high",
            "feature_verification": "verified",
            "pricing_transparency": "clear"
        }},
        "information_accuracy": 0.9,
        "source_reliability": 0.85
    }}
```
    """
    
    CONTENT_ANALYSIS_MUTUAL_FUNDS = """
    Analyze this mutual fund content focusing on performance metrics, fees, risk ratings, and investment strategy. The user's query is: "{query}"

    Content:
    {content}
    
    CRITICAL: If the query asks for specific fund recommendations (e.g., "best mutual funds for beginners", "name best funds"), you MUST:
    1. Identify ALL specific fund names mentioned with their ticker symbols
    2. Extract key details for each fund (expense ratio, minimum investment, risk level, performance)
    3. Provide SPECIFIC recommendations in the "recommendations" field, not generic advice
    4. Include fund names and why they're recommended in the "key_entities" field
    
    Provide analysis in JSON format, wrapped in fenced JSON blocks:

```json
{{
        "themes": ["Investment Strategy", "Performance Metrics", "Risk Assessment", "Fund Recommendations"],
        "quality_metrics": {{
            "data_completeness": 0.8,
            "performance_analysis": 0.9,
            "risk_disclosure": 0.7,
            "specificity": 0.9
        }},
        "recommendations": [
            "Vanguard 500 Index Fund (VFIAX): 0.04% expense ratio, $3,000 minimum, suitable for beginners seeking low-cost diversification",
            "Fidelity 500 Index Fund (FXAIX): 0.015% expense ratio, no minimum, ideal for cost-conscious beginners"
        ],
        "key_entities": [
            "Vanguard 500 Index Fund (VFIAX)",
            "Fidelity 500 Index Fund (FXAIX)",
            "Vanguard Total Bond Market Index Fund (VBTLX)"
        ],
        "credibility_indicators": {{
            "data_source": "reliable",
            "performance_verification": "verified",
            "regulatory_compliance": "compliant"
        }},
        "information_accuracy": 0.9,
        "source_reliability": 0.9
    }}
```

    IMPORTANT: The "recommendations" field should contain SPECIFIC fund recommendations with details when available, not generic advice. If specific funds are mentioned that match the query, list them with their key characteristics.
    """
    
    # Summarization Prompts
    SUMMARIZATION_BASE = """
    Create a comprehensive summary of the following content, focusing on aspects relevant to the query: "{query}" (Category: {category}).

    Content Title: {title}
    Maximum Summary Length: {max_length} characters
    
    Content:
    {content}
    
    CRITICAL INSTRUCTIONS:
    - If the query asks for specific recommendations (e.g., "best mutual funds", "name the best tools"), the executive summary MUST directly answer the query by listing specific names/recommendations
    - If the query asks "Name best X", include the actual names in the executive summary and key points
    - Key points should include specific recommendations, product names, or actionable items mentioned in the content
    - Do not provide generic summaries - provide direct answers to the query when specific information is available
    
    Please provide a summary in the following JSON format, wrapped in fenced JSON blocks:

```json
{{
        "executive_summary": "Direct answer to the query. If query asks for specific names/recommendations, list them here (e.g., 'The best mutual funds for beginners are: Vanguard 500 Index Fund (VFIAX), Fidelity 500 Index Fund (FXAIX)...') (max 300 chars)",
        "key_points": [
            "Specific recommendation 1 with details (e.g., 'Vanguard 500 Index Fund (VFIAX): 0.04% expense ratio, $3,000 minimum')",
            "Specific recommendation 2 with details",
            "Key point 3 (max 150 chars)"
        ],
        "detailed_summary": "Detailed paragraph summary that directly addresses the query. Include specific names, numbers, and actionable information when available (max {max_length} chars)",
        "main_topics": ["topic1", "topic2", "topic3"],
        "sentiment": "positive|negative|neutral",
        "confidence_score": 0.95
    }}
```
    
    Guidelines:
    - Executive summary should DIRECTLY ANSWER the query, not just describe the content
    - If the query asks "Name best X", the executive summary should list actual names
    - Key points should include specific recommendations with details (names, prices, features, etc.)
    - Detailed summary should provide comprehensive information that answers the query
    - Focus on information most relevant to "{query}"
    - Maintain factual accuracy and avoid speculation
    - Use clear, concise language
    - Prioritize actionable, specific information over generic descriptions
    """
    
    SUMMARIZATION_EXECUTIVE = """
    Create an executive-level summary of the following content for senior decision makers.

    Content:
    {content}
    
    Focus on:
    - High-level insights and implications
    - Strategic recommendations
    - Business impact and opportunities
    - Key metrics and data points
    
    Provide summary in JSON format, wrapped in fenced JSON blocks:

```json
{{
        "executive_summary": "Strategic overview in 1-2 sentences",
        "key_points": [
            "Strategic insight 1",
            "Business impact 2",
            "Recommendation 3"
        ],
        "detailed_summary": "Executive-level analysis and recommendations",
        "main_topics": ["strategy", "business_impact", "recommendations"],
        "sentiment": "positive|negative|neutral",
        "confidence_score": 0.9
    }}
```
    """
    
    SUMMARIZATION_TECHNICAL = """
    Create a technical summary of the following content for technical professionals.

    Content:
    {content}
    
    Focus on:
    - Technical specifications and requirements
    - Implementation details and architecture
    - Performance metrics and benchmarks
    - Technical challenges and solutions
    
    Provide summary in JSON format, wrapped in fenced JSON blocks:

```json
{{
        "executive_summary": "Technical overview in 1-2 sentences",
        "key_points": [
            "Technical specification 1",
            "Implementation detail 2",
            "Performance metric 3"
        ],
        "detailed_summary": "Technical analysis and implementation details",
        "main_topics": ["technical_specs", "implementation", "performance"],
        "sentiment": "positive|negative|neutral",
        "confidence_score": 0.9
    }}
```
    """
    
    # Structured Data Extraction Prompts
    EXTRACTION_BASE = """
    Extract structured data from the following content, focusing on {focus} relevant to the query: "{query}".

    Content Title: {title}
    Content URL: {url}
    
    Content:
    {content}
    
    Please extract and structure the information in the following JSON format, wrapped in fenced JSON blocks:

```json
{{
        "entities": [
            {{
                "type": "person|organization|product|technology|concept|location",
                "name": "entity name",
                "properties": {{
                    "description": "brief description",
                    "relevance": 0.9,
                    "confidence": 0.95
                }}
            }}
        ],
        "key_value_pairs": {{
            "key1": "value1",
            "key2": "value2"
        }},
        "categories": ["category1", "category2"],
        "confidence_scores": {{
            "key1": 0.95,
            "key2": 0.88
        }},
        "tables": [
            {{
                "title": "table title",
                "headers": ["col1", "col2"],
                "rows": [["row1col1", "row1col2"]]
            }}
        ],
        "measurements": [
            {{
                "type": "price|percentage|dimension|weight|time",
                "value": "actual value",
                "unit": "unit of measurement",
                "context": "what this measurement refers to"
            }}
        ]
    }}
```
    
    Focus on extracting {entities} and {key_values} that would be most valuable for someone searching for "{query}".
    Be precise and include confidence scores for extracted data.
    """
    
    EXTRACTION_AI_TOOLS = """
    Extract structured data specifically for AI tools and technologies.

    Content:
    {content}
    
    Focus on extracting:
    - Tool names and companies
    - Features and capabilities
    - Pricing and licensing
    - Technical specifications
    - Integration options
    - Target use cases
    
    Provide extraction in JSON format, wrapped in fenced JSON blocks:

```json
{{
        "entities": [
            {{
                "type": "ai_tool|company|technology",
                "name": "tool/company name",
                "properties": {{
                    "category": "tool category",
                    "features": ["feature1", "feature2"],
                    "pricing_model": "pricing type"
                }}
            }}
        ],
        "key_value_pairs": {{
            "pricing": "price information",
            "launch_date": "launch date",
            "supported_platforms": "platform list"
        }},
        "categories": ["AI Tools", "Machine Learning", "Productivity"],
        "confidence_scores": {{
            "pricing": 0.9,
            "features": 0.95
        }}
    }}
```
    """
    
    EXTRACTION_MUTUAL_FUNDS = """
    Extract structured data specifically for mutual funds and investment products. The user's query is: "{query}"

    Content:
    {content}
    
    CRITICAL: If the query asks for specific fund recommendations (e.g., "best mutual funds for beginners", "low risk funds"), you MUST extract:
    - SPECIFIC FUND NAMES with their ticker symbols (e.g., "Vanguard 500 Index Fund (VFIAX)")
    - Expense ratios (e.g., "0.04%")
    - Minimum investment amounts (e.g., "$3,000")
    - Risk levels (e.g., "low", "moderate", "high")
    - Performance metrics (e.g., "8.19% annual return")
    - Why each fund is recommended (e.g., "suitable for beginners", "low cost", "diversified")
    
    For each fund mentioned, extract ALL available details. Prioritize funds that match the query criteria (e.g., "beginners", "low risk").
    
    Provide extraction in JSON format, wrapped in fenced JSON blocks:

```json
{{
        "entities": [
            {{
                "type": "mutual_fund",
                "name": "Full Fund Name (Ticker Symbol)",
                "properties": {{
                    "ticker": "TICKER",
                    "category": "fund category (e.g., Index Fund, Target Date Fund)",
                    "strategy": "investment strategy",
                    "risk_level": "low|moderate|high",
                    "suitable_for": "who this fund is for (e.g., beginners, retirement)",
                    "expense_ratio": "0.XX%",
                    "minimum_investment": "$X,XXX",
                    "performance_annual": "X.XX%",
                    "why_recommended": "specific reason this fund matches the query",
                    "relevance": 0.95
                }}
            }}
        ],
        "key_value_pairs": {{
            "recommended_funds": [
                {{
                    "name": "Fund Name",
                    "ticker": "TICKER",
                    "expense_ratio": "0.XX%",
                    "minimum_investment": "$X,XXX",
                    "risk_level": "low|moderate|high",
                    "why_recommended": "specific reason"
                }}
            ],
            "expense_ratio": "expense ratio percentage",
            "minimum_investment": "minimum amount",
            "performance_1yr": "1-year return"
        }},
        "categories": ["Mutual Funds", "Investment Products", "Retirement Planning"],
        "confidence_scores": {{
            "expense_ratio": 0.95,
            "performance": 0.9,
            "fund_recommendations": 0.9
        }}
    }}
```

    IMPORTANT: If the content contains specific fund recommendations that match the query, extract them as separate entities with full details. Do not just extract generic concepts - extract actual fund names, tickers, and actionable information.
    """
    
    # Duplicate Detection Prompts
    DUPLICATE_DETECTION = """
    Analyze the similarity between these two content pieces and provide a similarity score from 0.0 to 1.0.
    
    Content 1:
    Title: {title1}
    Content: {content1}
    
    Content 2:
    Title: {title2}
    Content: {content2}
    
    Consider:
    - Topic and theme similarity
    - Information overlap
    - Writing style and structure
    - Key points and arguments
    
    Provide only a JSON response with the similarity score, wrapped in fenced JSON blocks:

```json
{{"similarity_score": 0.85}}
```
    """
    
    # Quality Assessment Prompts
    QUALITY_ASSESSMENT = """
    Assess the quality and credibility of the following content.

    Content:
    {content}
    
    Evaluate:
    - Information accuracy and reliability
    - Source credibility and authority
    - Content depth and comprehensiveness
    - Writing quality and clarity
    - Factual verification and citations
    
    Provide assessment in JSON format, wrapped in fenced JSON blocks:

```json
{{
        "overall_quality": 0.85,
        "information_accuracy": 0.9,
        "source_reliability": 0.8,
        "content_depth": 0.85,
        "writing_quality": 0.9,
        "credibility_factors": {{
            "expert_analysis": true,
            "recent_sources": true,
            "peer_reviewed": false,
            "factual_verification": "high"
        }},
        "quality_indicators": [
            "Well-researched content",
            "Clear and logical structure",
            "Reliable source citations"
        ]
    }}
```
    """
    
    # Entity Extraction Prompts
    ENTITY_EXTRACTION = """
    Extract named entities and key information from the following content.

    Content:
    {content}
    
    Extract:
    - People (names, titles, roles)
    - Organizations (companies, institutions, groups)
    - Products and services
    - Technologies and tools
    - Locations and places
    - Dates and time periods
    - Numbers and measurements
    
    Provide extraction in JSON format, wrapped in fenced JSON blocks:

```json
{{
        "people": [
            {{
                "name": "person name",
                "title": "job title",
                "role": "role description",
                "confidence": 0.95
            }}
        ],
        "organizations": [
            {{
                "name": "organization name",
                "type": "organization type",
                "industry": "industry sector",
                "confidence": 0.9
            }}
        ],
        "products": [
            {{
                "name": "product name",
                "category": "product category",
                "features": ["feature1", "feature2"],
                "confidence": 0.85
            }}
        ],
        "technologies": [
            {{
                "name": "technology name",
                "type": "technology type",
                "description": "brief description",
                "confidence": 0.9
            }}
        ]
    }}
```
    """
    
    @classmethod
    def get_analysis_prompt(cls, query: str, category: str, title: str = "", url: str = "", content: str = "") -> str:
        """Get content analysis prompt with variables substituted and input validation."""
        # Validate inputs
        cls._validate_input_static(query=query, category=category, title=title, url=url, content=content)
        
        if category == "ai_tools":
            base_prompt = cls.CONTENT_ANALYSIS_AI_TOOLS
        elif category == "mutual_funds":
            base_prompt = cls.CONTENT_ANALYSIS_MUTUAL_FUNDS
        else:
            base_prompt = cls.CONTENT_ANALYSIS_BASE
        
        return base_prompt.format(
            query=query,
            category=category,
            title=title,
            url=url,
            content=content,
            specific_use_case="AI development and automation"
        )
    
    @classmethod
    def get_summary_prompt(cls, query: str, category: str, title: str = "", content: str = "", max_length: Optional[int] = None, style: str = "base") -> str:
        """Get summarization prompt with variables substituted and configurable length limits."""
        # Validate inputs
        cls._validate_input_static(query=query, category=category, title=title, content=content, style=style)
        
        # Use configurable length limit from settings
        if max_length is None:
            max_length = cls._get_configurable_limit_static("summary_length", 500)
        
        # Validate max_length
        if max_length <= 0:
            raise ValueError("max_length must be positive")
        
        if style == "executive":
            base_prompt = cls.SUMMARIZATION_EXECUTIVE
        elif style == "technical":
            base_prompt = cls.SUMMARIZATION_TECHNICAL
        else:
            base_prompt = cls.SUMMARIZATION_BASE
        
        return base_prompt.format(
            query=query,
            category=category,
            title=title,
            content=content,
            max_length=max_length
        )
    
    @classmethod
    def get_extraction_prompt(cls, query: str, category: str, title: str = "", url: str = "", content: str = "", focus: str = "", entities: str = "", key_values: str = "") -> str:
        """Get structured data extraction prompt with variables substituted and input validation."""
        # Validate inputs
        cls._validate_input_static(query=query, category=category, title=title, url=url, content=content)
        
        if category == "ai_tools":
            base_prompt = cls.EXTRACTION_AI_TOOLS
        elif category == "mutual_funds":
            base_prompt = cls.EXTRACTION_MUTUAL_FUNDS
        else:
            base_prompt = cls.EXTRACTION_BASE
        
        return base_prompt.format(
            query=query,
            category=category,
            title=title,
            url=url,
            content=content,
            focus=focus or "key information",
            entities=entities or "entities and concepts",
            key_values=key_values or "key data points"
        )
    
    @classmethod
    def get_duplicate_detection_prompt(cls, title1: str, content1: str, title2: str, content2: str, max_length: Optional[int] = None) -> str:
        """Get duplicate detection prompt with variables substituted and configurable content length limits."""
        # Validate inputs
        cls._validate_input_static(title1=title1, content1=content1, title2=title2, content2=content2)
        
        # Use configurable content length limit from settings
        if max_length is None:
            max_length = cls._get_configurable_limit_static("similarity_content", 1000)
        
        # Validate max_length
        if max_length <= 0:
            raise ValueError("max_length must be positive")
        
        return cls.DUPLICATE_DETECTION.format(
            title1=title1,
            content1=content1[:max_length],  # Use configurable content length limit
            title2=title2,
            content2=content2[:max_length]
        )
    
    @classmethod
    def get_quality_assessment_prompt(cls, content: str) -> str:
        """Get quality assessment prompt with variables substituted and configurable content length limits."""
        # Validate inputs
        cls._validate_input_static(content=content)
        
        # Use configurable content length limit
        max_length = cls._get_configurable_limit_static("extraction_content", 2000)
        
        return cls.QUALITY_ASSESSMENT.format(content=content[:max_length])
    
    @classmethod
    def get_entity_extraction_prompt(cls, content: str) -> str:
        """Get entity extraction prompt with variables substituted and configurable content length limits."""
        # Validate inputs
        cls._validate_input_static(content=content)
        
        # Use configurable content length limit
        max_length = cls._get_configurable_limit_static("extraction_content", 2000)
        
        return cls.ENTITY_EXTRACTION.format(content=content[:max_length])
    
    @classmethod
    def _validate_input_static(cls, **kwargs) -> None:
        """Static method to validate input parameters for prompt generation."""
        for key, value in kwargs.items():
            if value is None:
                raise ValueError(f"Required parameter '{key}' cannot be None")
            if isinstance(value, str) and len(value.strip()) == 0:
                raise ValueError(f"Required parameter '{key}' cannot be empty")
    
    @classmethod
    def _get_configurable_limit_static(cls, limit_type: str, default: int) -> int:
        """Static method to get configurable limit from settings or use default."""
        try:
            from app.core.config import get_settings
            settings = get_settings()
            
            if limit_type == "summary_length":
                return getattr(settings, 'processing_max_summary_length', default)
            elif limit_type == "similarity_content":
                return getattr(settings, 'gemini_max_similarity_content_length', default)
            elif limit_type == "extraction_content":
                return getattr(settings, 'gemini_max_content_length', default)
            else:
                return default
        except Exception:
            return default
