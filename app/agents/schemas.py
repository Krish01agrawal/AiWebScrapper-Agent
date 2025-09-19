from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class QueryCategory(str, Enum):
    """Enumeration of query categories."""
    AI_TOOLS = "ai_tools"
    MUTUAL_FUNDS = "mutual_funds"
    GENERAL = "general"
    UNKNOWN = "unknown"


class BaseQueryResult(BaseModel):
    """Base class for query results with common fields."""
    query_text: str = Field(..., description="Original query text")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the result")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the query was processed")
    processing_time: float = Field(..., ge=0.0, description="Processing time in seconds")
    category: QueryCategory = Field(..., description="Categorized domain of the query")


class AIToolsQuery(BaseModel):
    """Schema for AI tools related queries."""
    tool_type: Optional[str] = Field(None, description="Type of AI tool (e.g., image generation, text analysis)")
    use_case: Optional[str] = Field(None, description="Intended use case for the tool")
    features_required: Optional[List[str]] = Field(None, description="Required features or capabilities")
    budget_range: Optional[str] = Field(None, description="Budget range for the tool")
    technical_expertise: Optional[str] = Field(None, description="Required technical expertise level")


class MutualFundsQuery(BaseModel):
    """Schema for mutual funds related queries."""
    investment_type: Optional[str] = Field(None, description="Type of investment (e.g., equity, debt, hybrid)")
    risk_level: Optional[str] = Field(None, description="Risk tolerance level")
    time_horizon: Optional[str] = Field(None, description="Investment time horizon")
    amount_range: Optional[str] = Field(None, description="Investment amount range")
    investment_goal: Optional[str] = Field(None, description="Primary investment goal")


class GeneralQuery(BaseModel):
    """Schema for general queries that don't fit specific categories."""
    intent: Optional[str] = Field(None, description="General intent of the query")
    entities: Optional[List[str]] = Field(None, description="Key entities mentioned in the query")
    context: Optional[str] = Field(None, description="Additional context or details")


class ParsedQuery(BaseModel):
    """Main schema containing the categorized query result."""
    base_result: BaseQueryResult = Field(..., description="Base query result information")
    ai_tools_data: Optional[AIToolsQuery] = Field(None, description="AI tools specific data if applicable")
    mutual_funds_data: Optional[MutualFundsQuery] = Field(None, description="Mutual funds specific data if applicable")
    general_data: Optional[GeneralQuery] = Field(None, description="General query data if applicable")
    raw_entities: Optional[Dict[str, Any]] = Field(None, description="Raw extracted entities from the query")
    suggestions: Optional[List[str]] = Field(None, description="Suggested follow-up actions or clarifications")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "base_result": {
                    "query_text": "Find AI tools for image generation",
                    "confidence_score": 0.95,
                    "timestamp": "2024-01-01T12:00:00Z",
                    "processing_time": 1.2,
                    "category": "ai_tools"
                },
                "ai_tools_data": {
                    "tool_type": "image generation",
                    "use_case": "creative design",
                    "features_required": ["high resolution", "multiple styles"],
                    "budget_range": "free to $50/month",
                    "technical_expertise": "beginner"
                }
            }
        }
    }
