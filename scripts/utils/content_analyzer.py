#!/usr/bin/env python3
"""
Content quality analyzer utility for validating scraped content relevance and quality.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from urllib.parse import urlparse


class RelevanceMetrics(BaseModel):
    """Pydantic model for relevance scores and metrics."""
    url_relevance: float = Field(..., ge=0.0, le=1.0, description="URL domain relevance score")
    title_relevance: float = Field(..., ge=0.0, le=1.0, description="Title relevance score")
    content_relevance: float = Field(..., ge=0.0, le=1.0, description="Content snippet relevance score")
    overall_relevance: float = Field(..., ge=0.0, le=1.0, description="Overall relevance score")
    issues: List[str] = Field(default_factory=list, description="List of relevance issues found")


class ContentQualityAnalyzer:
    """Content quality analyzer for validating scraped content relevance."""
    
    # Domain-specific relevant domains
    AI_TOOLS_DOMAINS = {
        "github.com", "huggingface.co", "openai.com", "anthropic.com", 
        "replicate.com", "stability.ai", "cohere.com", "together.ai",
        "perplexity.ai", "claude.ai", "chatgpt.com", "bard.google.com"
    }
    
    MUTUAL_FUNDS_DOMAINS = {
        "morningstar.com", "moneycontrol.com", "valueresearchonline.com",
        "etmoney.com", "groww.in", "zerodha.com", "paytmmoney.com",
        "vanguard.com", "fidelity.com", "schwab.com", "blackrock.com"
    }
    
    # Category-specific keywords
    AI_TOOLS_KEYWORDS = {
        "ai", "agent", "model", "llm", "neural", "machine learning", 
        "deep learning", "nlp", "generative", "transformer", "gpt", 
        "claude", "coding", "development", "programming", "software"
    }
    
    MUTUAL_FUNDS_KEYWORDS = {
        "fund", "nav", "return", "equity", "debt", "sip", "mutual",
        "investment", "portfolio", "expense ratio", "aum", "scheme",
        "retirement", "planning", "index", "etf"
    }
    
    def analyze_url_relevance(self, url: str, query_category: str) -> float:
        """Score URL domain relevance (0.0-1.0).
        
        Args:
            url: URL to analyze
            query_category: Query category (ai_tools, mutual_funds, general)
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www. prefix if present
            if domain.startswith("www."):
                domain = domain[4:]
            
            if query_category == "ai_tools":
                if domain in self.AI_TOOLS_DOMAINS:
                    return 0.9
                # Check for partial matches
                for relevant_domain in self.AI_TOOLS_DOMAINS:
                    if relevant_domain in domain or domain in relevant_domain:
                        return 0.8
                # Check for AI-related subdomains
                if any(keyword in domain for keyword in ["ai", "ml", "tech", "dev", "code"]):
                    return 0.6
                return 0.3
            
            elif query_category == "mutual_funds":
                if domain in self.MUTUAL_FUNDS_DOMAINS:
                    return 0.9
                # Check for partial matches
                for relevant_domain in self.MUTUAL_FUNDS_DOMAINS:
                    if relevant_domain in domain or domain in relevant_domain:
                        return 0.8
                # Check for finance-related subdomains
                if any(keyword in domain for keyword in ["finance", "money", "invest", "fund", "bank"]):
                    return 0.6
                return 0.3
            
            else:  # general category
                # Broader matching for general queries
                return 0.5
        
        except Exception:
            return 0.0
    
    def analyze_title_relevance(self, title: str, query_text: str, query_category: str) -> float:
        """Score title relevance.
        
        Args:
            title: Page title to analyze
            query_text: Original query text
            query_category: Query category
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        if not title:
            return 0.0
        
        title_lower = title.lower()
        query_lower = query_text.lower()
        
        # Extract query keywords
        query_words = set(query_lower.split())
        
        # Count keyword matches
        matches = sum(1 for word in query_words if word in title_lower and len(word) > 2)
        
        # Category-specific keyword matching
        category_keywords = set()
        if query_category == "ai_tools":
            category_keywords = self.AI_TOOLS_KEYWORDS
        elif query_category == "mutual_funds":
            category_keywords = self.MUTUAL_FUNDS_KEYWORDS
        
        category_matches = sum(1 for keyword in category_keywords if keyword in title_lower)
        
        # Calculate score
        total_matches = matches + category_matches
        
        if total_matches >= 3:
            return 0.9
        elif total_matches >= 2:
            return 0.7
        elif total_matches >= 1:
            return 0.5
        else:
            return 0.3
    
    def analyze_content_snippet(
        self, 
        content: str, 
        query_text: str, 
        query_category: str, 
        max_length: int = 500
    ) -> float:
        """Score content relevance.
        
        Args:
            content: Content text to analyze
            query_text: Original query text
            query_category: Query category
            max_length: Maximum length of content snippet to analyze
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        if not content:
            return 0.0
        
        # Extract first N characters
        snippet = content[:max_length].lower()
        query_lower = query_text.lower()
        
        # Extract query keywords
        query_words = [w for w in query_lower.split() if len(w) > 2]
        
        # Count keyword occurrences
        keyword_count = sum(snippet.count(word) for word in query_words)
        
        # Category-specific keyword matching
        category_keywords = set()
        if query_category == "ai_tools":
            category_keywords = self.AI_TOOLS_KEYWORDS
        elif query_category == "mutual_funds":
            category_keywords = self.MUTUAL_FUNDS_KEYWORDS
        
        category_count = sum(snippet.count(keyword) for keyword in category_keywords)
        
        # Calculate keyword density
        total_keywords = keyword_count + category_count
        snippet_length = len(snippet.split())
        
        if snippet_length == 0:
            return 0.0
        
        keyword_density = total_keywords / snippet_length
        
        # Score based on density and absolute count
        if keyword_density > 0.1 or total_keywords >= 5:
            return 0.8
        elif keyword_density > 0.05 or total_keywords >= 3:
            return 0.6
        elif keyword_density > 0.02 or total_keywords >= 1:
            return 0.4
        else:
            return 0.2
    
    def analyze_ai_insights_quality(
        self, 
        ai_insights: Dict[str, Any], 
        query_text: str, 
        query_category: str
    ) -> Dict[str, Any]:
        """Validate AI analysis quality.
        
        Args:
            ai_insights: AI insights dictionary from response
            query_text: Original query text
            query_category: Query category
            
        Returns:
            Quality report with scores and issues
        """
        issues = []
        scores = {}
        
        # Check themes
        themes = ai_insights.get("themes", [])
        if not themes:
            issues.append("No themes found in AI insights")
            scores["themes_score"] = 0.0
        else:
            # Check if themes include query keywords
            query_lower = query_text.lower()
            theme_matches = sum(1 for theme in themes if any(word in theme.lower() for word in query_lower.split()))
            if theme_matches > 0:
                scores["themes_score"] = 0.8
            else:
                scores["themes_score"] = 0.4
                issues.append("Themes don't match query keywords")
        
        # Check confidence scores
        confidence = ai_insights.get("confidence_score", 0.0)
        if confidence < 0.5:
            issues.append(f"Low confidence score: {confidence}")
            scores["confidence_score"] = 0.3
        elif confidence >= 0.7:
            scores["confidence_score"] = 0.9
        else:
            scores["confidence_score"] = 0.6
        
        # Check relevance score
        relevance = ai_insights.get("relevance_score", 0.0)
        if relevance < 0.5:
            issues.append(f"Low relevance score: {relevance}")
            scores["relevance_score"] = 0.3
        elif relevance >= 0.7:
            scores["relevance_score"] = 0.9
        else:
            scores["relevance_score"] = 0.6
        
        # Check recommendations
        recommendations = ai_insights.get("recommendations", [])
        if not recommendations:
            issues.append("No recommendations provided")
            scores["recommendations_score"] = 0.0
        elif len(recommendations) >= 2:
            scores["recommendations_score"] = 0.8
        else:
            scores["recommendations_score"] = 0.5
        
        # Calculate overall quality
        if scores:
            overall_quality = sum(scores.values()) / len(scores)
        else:
            overall_quality = 0.0
        
        return {
            "overall_quality": overall_quality,
            "scores": scores,
            "issues": issues,
            "has_issues": len(issues) > 0
        }
    
    def analyze_structured_data_quality(
        self, 
        structured_data: Dict[str, Any], 
        query_category: str
    ) -> Dict[str, Any]:
        """Validate structured data extraction.
        
        Args:
            structured_data: Structured data dictionary from response
            query_category: Query category
            
        Returns:
            Quality report with entity count and relevance scores
        """
        issues = []
        
        # Check entities
        entities = structured_data.get("entities", [])
        entity_count = len(entities)
        
        if entity_count < 3:
            issues.append(f"Low entity count: {entity_count} (expected at least 3)")
        
        # Check entity relevance for category
        if query_category == "ai_tools":
            relevant_entity_types = {"product", "company", "tool", "model", "technology"}
        elif query_category == "mutual_funds":
            relevant_entity_types = {"fund", "company", "scheme", "investment", "financial"}
        else:
            relevant_entity_types = set()
        
        relevant_entities = 0
        for entity in entities:
            entity_type = entity.get("type", "").lower()
            if entity_type in relevant_entity_types:
                relevant_entities += 1
        
        # Check key-value pairs
        key_value_pairs = structured_data.get("key_value_pairs", {})
        if not key_value_pairs:
            issues.append("No key-value pairs extracted")
        else:
            # Check for meaningful (non-empty) values
            empty_values = sum(1 for v in key_value_pairs.values() if not v or v == "")
            if empty_values > 0:
                issues.append(f"{empty_values} empty key-value pairs found")
        
        # Check confidence scores
        confidence_scores = structured_data.get("confidence_scores", {})
        low_confidence_count = sum(1 for score in confidence_scores.values() if score < 0.5)
        if low_confidence_count > 0:
            issues.append(f"{low_confidence_count} low confidence scores found")
        
        # Calculate quality metrics
        quality_score = 0.0
        if entity_count >= 3:
            quality_score += 0.4
        elif entity_count >= 1:
            quality_score += 0.2
        
        if len(key_value_pairs) >= 3:
            quality_score += 0.3
        elif len(key_value_pairs) >= 1:
            quality_score += 0.15
        
        if relevant_entities > 0:
            quality_score += 0.3
        elif entity_count > 0:
            quality_score += 0.1
        
        return {
            "entity_count": entity_count,
            "relevant_entities": relevant_entities,
            "key_value_pairs_count": len(key_value_pairs),
            "quality_score": quality_score,
            "issues": issues,
            "has_issues": len(issues) > 0
        }
    
    def analyze_content_relevance(
        self,
        url: str,
        title: str,
        content: str,
        query_text: str,
        query_category: str
    ) -> RelevanceMetrics:
        """Comprehensive content relevance analysis.
        
        Args:
            url: Content URL
            title: Content title
            content: Content text
            query_text: Original query text
            query_category: Query category
            
        Returns:
            RelevanceMetrics with all scores
        """
        url_score = self.analyze_url_relevance(url, query_category)
        title_score = self.analyze_title_relevance(title, query_text, query_category)
        content_score = self.analyze_content_snippet(content, query_text, query_category)
        
        # Calculate overall relevance (weighted average)
        overall_relevance = (url_score * 0.3 + title_score * 0.3 + content_score * 0.4)
        
        # Collect issues
        issues = []
        if url_score < 0.5:
            issues.append(f"Low URL relevance: {url_score:.2f}")
        if title_score < 0.5:
            issues.append(f"Low title relevance: {title_score:.2f}")
        if content_score < 0.5:
            issues.append(f"Low content relevance: {content_score:.2f}")
        
        return RelevanceMetrics(
            url_relevance=url_score,
            title_relevance=title_score,
            content_relevance=content_score,
            overall_relevance=overall_relevance,
            issues=issues
        )

