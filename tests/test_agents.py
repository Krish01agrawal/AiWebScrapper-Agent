import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.agents.base import BaseAgent
from app.agents.schemas import QueryCategory, ParsedQuery, BaseQueryResult
from app.agents.processor import QueryProcessor
from app.agents.parsers import NaturalLanguageParser
from app.agents.categorizer import DomainCategorizer
from app.core.config import Settings


class TestBaseAgent:
    """Test cases for BaseAgent class."""
    
    def test_base_agent_initialization(self):
        """Test BaseAgent initialization."""
        agent = MockBaseAgent("TestAgent", "Test Description")
        
        assert agent.name == "TestAgent"
        assert agent.description == "Test Description"
        assert agent.version == "1.0.0"
        assert isinstance(agent.created_at, datetime)
    
    def test_base_agent_info(self):
        """Test get_info method."""
        agent = MockBaseAgent("TestAgent", "Test Description")
        info = agent.get_info()
        
        assert info["name"] == "TestAgent"
        assert info["description"] == "Test Description"
        assert info["version"] == "1.0.0"
        assert info["type"] == "MockBaseAgent"
        assert "timeout_seconds" in info
    
    def test_base_agent_string_representation(self):
        """Test string representation."""
        agent = MockBaseAgent("TestAgent", "Test Description")
        
        assert str(agent) == "MockBaseAgent(name='TestAgent', version='1.0.0')"
        assert repr(agent) == "MockBaseAgent(name='TestAgent', version='1.0.0')"
    
    def test_agent_specific_timeout_detection(self):
        """Test that agents get appropriate timeouts based on their names."""
        parser_agent = MockBaseAgent("NaturalLanguageParser", "Parser")
        categorizer_agent = MockBaseAgent("DomainCategorizer", "Categorizer")
        processor_agent = MockBaseAgent("QueryProcessor", "Processor")
        generic_agent = MockBaseAgent("GenericAgent", "Generic")
        
        # Test timeout detection
        assert parser_agent._get_agent_timeout() == 45  # parser_timeout_seconds
        assert categorizer_agent._get_agent_timeout() == 30  # categorizer_timeout_seconds
        assert processor_agent._get_agent_timeout() == 60  # processor_timeout_seconds
        assert generic_agent._get_agent_timeout() == 30  # default agent_timeout_seconds


class MockBaseAgent(BaseAgent):
    """Mock implementation of BaseAgent for testing."""
    
    async def execute(self, *args, **kwargs):
        return "mock_result"


class TestNaturalLanguageParser:
    """Test cases for NaturalLanguageParser class."""
    
    @pytest.fixture
    def mock_gemini_client(self):
        """Mock Gemini client."""
        client = Mock()
        client.generate_content = AsyncMock()
        return client
    
    @pytest.fixture
    def parser(self, mock_gemini_client):
        """Parser instance with mock client."""
        return NaturalLanguageParser(mock_gemini_client)
    
    def test_parser_initialization(self, mock_gemini_client):
        """Test parser initialization."""
        parser = NaturalLanguageParser(mock_gemini_client)
        
        assert parser.name == "NaturalLanguageParser"
        assert parser.description == "Parses natural language queries using Gemini AI"
        assert parser.version == "1.0.0"
    
    def test_create_parsing_prompt(self, parser):
        """Test prompt creation."""
        query = "Find AI tools for image generation"
        prompt = parser._create_parsing_prompt(query)
        
        assert query in prompt
        assert "intent" in prompt
        assert "entities" in prompt
        assert "domain" in prompt
        assert "confidence" in prompt
    
    def test_validate_parsed_data(self, parser):
        """Test data validation."""
        # Valid data
        valid_data = {
            "intent": "search",
            "entities": ["AI", "tools"],
            "domain": "ai_tools",
            "confidence": 0.9
        }
        result = parser._validate_parsed_data(valid_data)
        
        assert result["intent"] == "search"
        assert result["entities"] == ["AI", "tools"]
        assert result["confidence"] == 0.9
        
        # Missing fields
        incomplete_data = {"intent": "search"}
        result = parser._validate_parsed_data(incomplete_data)
        
        assert result["entities"] == []
        assert result["confidence"] == 0.5
    
    def test_fallback_parsing(self, parser):
        """Test fallback parsing."""
        response = "This is a response about AI tools"
        result = parser._fallback_parsing(response)
        
        assert result["domain"] == "ai_tools"
        assert result["confidence"] == 0.3
        assert "Fallback parsing used" in result["additional_context"]
    
    @pytest.mark.asyncio
    async def test_parse_gemini_response_success(self, parser):
        """Test successful JSON parsing from Gemini response."""
        response_text = '{"intent": "search", "entities": ["AI"], "domain": "ai_tools", "confidence": 0.8}'
        result = await parser._parse_gemini_response(response_text)
        
        assert result["intent"] == "search"
        assert result["entities"] == ["AI"]
        assert result["domain"] == "ai_tools"
        assert result["confidence"] == 0.8
    
    @pytest.mark.asyncio
    async def test_parse_gemini_response_malformed_json(self, parser):
        """Test handling of malformed JSON responses."""
        response_text = '{"intent": "search", "entities": ["AI", "domain": "ai_tools"}'  # Missing closing brace
        result = await parser._parse_gemini_response(response_text)
        
        assert result["domain"] == "ai_tools"  # Should use fallback
        assert result["confidence"] == 0.3
    
    @pytest.mark.asyncio
    async def test_parse_gemini_response_large_json(self, parser):
        """Test handling of very large JSON responses."""
        # Create a large JSON response
        large_data = {"data": "x" * 15000}  # 15KB response
        response_text = json.dumps(large_data)
        result = await parser._parse_gemini_response(response_text)
        
        # Should use fallback due to size limit
        assert result["domain"] == "general"
        assert result["confidence"] == 0.3
    
    @pytest.mark.asyncio
    async def test_parse_gemini_response_no_json(self, parser):
        """Test handling of responses without JSON."""
        response_text = "Hello world. This is a simple test message."
        result = await parser._parse_gemini_response(response_text)
        
        # Should use fallback parsing and detect general domain
        assert result["domain"] == "general"
        assert result["confidence"] == 0.3


class TestDomainCategorizer:
    """Test cases for DomainCategorizer class."""
    
    @pytest.fixture
    def mock_gemini_client(self):
        """Mock Gemini client."""
        client = Mock()
        client.generate_content = AsyncMock()
        return client
    
    @pytest.fixture
    def categorizer(self, mock_gemini_client):
        """Categorizer instance with mock client."""
        return DomainCategorizer(mock_gemini_client)
    
    def test_categorizer_initialization(self, mock_gemini_client):
        """Test categorizer initialization."""
        categorizer = DomainCategorizer(mock_gemini_client)
        
        assert categorizer.name == "DomainCategorizer"
        assert "ai_tools" in categorizer.keyword_rules
        assert "mutual_funds" in categorizer.keyword_rules
    
    def test_rule_based_categorization(self, categorizer):
        """Test rule-based categorization."""
        # AI tools query
        ai_query = {
            "raw_query": "Find AI tools for machine learning",
            "entities": ["AI", "machine learning"]
        }
        category, confidence = categorizer._rule_based_categorization(ai_query)
        
        assert category == QueryCategory.AI_TOOLS
        # Confidence should be > 0.3 (minimum threshold) but may be lower due to many keywords
        assert confidence > 0.3
        
        # Mutual funds query
        finance_query = {
            "raw_query": "Best mutual funds for investment",
            "entities": ["mutual funds", "investment"]
        }
        category, confidence = categorizer._rule_based_categorization(finance_query)
        
        assert category == QueryCategory.MUTUAL_FUNDS
        assert confidence > 0.3
        
        # General query
        general_query = {
            "raw_query": "How to cook pasta",
            "entities": ["cooking", "pasta"]
        }
        category, confidence = categorizer._rule_based_categorization(general_query)
        
        assert category == QueryCategory.GENERAL
        assert confidence > 0.3
    
    def test_create_categorization_prompt(self, categorizer):
        """Test prompt creation for LLM categorization."""
        parsed_data = {
            "raw_query": "Find AI tools",
            "intent": "search",
            "entities": ["AI", "tools"]
        }
        
        prompt = categorizer._create_categorization_prompt(parsed_data)
        
        assert "Find AI tools" in prompt
        # The prompt should contain the general categorization template content
        assert "intent" in prompt
        assert "entities" in prompt
        assert "context" in prompt
        assert "category" in prompt
    
    @pytest.mark.asyncio
    async def test_llm_categorization_success(self, mock_gemini_client, categorizer):
        """Test successful LLM categorization."""
        mock_gemini_client.generate_content.return_value = Mock(
            text='{"category": "ai_tools", "confidence": 0.9, "reasoning": "AI tools query"}'
        )
        
        parsed_data = {"raw_query": "Find AI tools", "intent": "search", "entities": ["AI"]}
        category, confidence = await categorizer._llm_categorization(parsed_data)
        
        assert category == QueryCategory.AI_TOOLS
        assert confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_llm_categorization_failure_fallback(self, mock_gemini_client, categorizer):
        """Test LLM categorization failure with fallback."""
        mock_gemini_client.generate_content.side_effect = Exception("API Error")
        
        parsed_data = {"raw_query": "Find AI tools", "intent": "search", "entities": ["AI"]}
        category, confidence = await categorizer._llm_categorization(parsed_data)
        
        assert category == QueryCategory.GENERAL
        assert confidence == 0.5
    
    @pytest.mark.asyncio
    async def test_parse_categorization_response_large_json(self, categorizer):
        """Test handling of large categorization responses."""
        large_data = {"category": "ai_tools", "data": "x" * 10000}  # 10KB response
        response_text = json.dumps(large_data)
        category, confidence = await categorizer._parse_categorization_response(response_text)
        
        # Should use fallback due to size limit
        assert category == QueryCategory.GENERAL
        assert confidence == 0.5


class TestQueryProcessor:
    """Test cases for QueryProcessor class."""
    
    @pytest.fixture
    def mock_gemini_client(self):
        """Mock Gemini client."""
        client = Mock()
        client.generate_content = AsyncMock()
        return client
    
    @pytest.fixture
    def processor(self, mock_gemini_client):
        """Processor instance with mock client."""
        return QueryProcessor(mock_gemini_client)
    
    def test_processor_initialization(self, mock_gemini_client):
        """Test processor initialization."""
        processor = QueryProcessor(mock_gemini_client)
        
        assert processor.name == "QueryProcessor"
        assert processor.description == "Orchestrates query parsing, categorization, and schema mapping"
        assert processor.version == "1.0.0"
        assert processor.parser is not None
        assert processor.categorizer is not None
    
    def test_create_parsed_query(self, processor):
        """Test creation of ParsedQuery object."""
        query_text = "Find AI tools for image generation"
        category = QueryCategory.AI_TOOLS
        confidence = 0.95
        processing_time = 1.5
        
        parsed_data = {
            "intent": "search",
            "entities": ["AI", "tools", "image generation"],
            "domain": "ai_tools"
        }
        
        domain_data = {
            "tool_type": "image generation",
            "use_case": "creative design",
            "features_required": ["high resolution"],
            "budget_range": "medium",
            "technical_expertise": "beginner"
        }
        
        result = processor._create_parsed_query(
            query_text=query_text,
            category=category,
            confidence=confidence,
            processing_time=processing_time,
            parsed_data=parsed_data,
            domain_data=domain_data
        )
        
        assert isinstance(result, ParsedQuery)
        assert result.base_result.query_text == query_text
        assert result.base_result.confidence_score == confidence
        assert result.base_result.processing_time == processing_time
        assert result.base_result.category == category
        assert result.ai_tools_data is not None
        assert result.ai_tools_data.tool_type == "image generation"
    
    def test_generate_suggestions(self, processor):
        """Test suggestion generation."""
        # High confidence AI tools query
        suggestions = processor._generate_suggestions(
            QueryCategory.AI_TOOLS, 0.9, {"tool_type": "image generation"}
        )
        
        assert "budget range" in " ".join(suggestions).lower()
        assert "technical expertise" in " ".join(suggestions).lower()
        
        # Low confidence query
        suggestions = processor._generate_suggestions(
            QueryCategory.GENERAL, 0.5, {}
        )
        
        assert "more specific details" in " ".join(suggestions).lower()
    
    def test_create_error_result(self, processor):
        """Test error result creation."""
        query_text = "Invalid query"
        error_message = "Processing failed"
        start_time = datetime.utcnow()
        
        result = processor._create_error_result(query_text, error_message, start_time)
        
        assert isinstance(result, ParsedQuery)
        assert result.base_result.query_text == query_text
        assert result.base_result.confidence_score == 0.0
        assert result.base_result.category == QueryCategory.UNKNOWN
        assert "Processing failed" in result.suggestions[0]
    
    @pytest.mark.asyncio
    async def test_extract_ai_tools_data_success(self, mock_gemini_client, processor):
        """Test successful AI tools data extraction."""
        mock_gemini_client.generate_content.return_value = Mock(
            text='{"tool_type": "image generation", "use_case": "design", "features_required": ["high res"], "budget_range": "medium", "technical_expertise": "beginner"}'
        )
        
        parsed_data = {"raw_query": "Find AI image tools", "intent": "search", "entities": ["AI", "image"]}
        result = await processor._extract_ai_tools_data(parsed_data)
        
        assert result["tool_type"] == "image generation"
        assert result["use_case"] == "design"
        assert "high res" in result["features_required"]
    
    @pytest.mark.asyncio
    async def test_extract_ai_tools_data_failure_fallback(self, mock_gemini_client, processor):
        """Test AI tools data extraction failure with fallback."""
        mock_gemini_client.generate_content.side_effect = Exception("API Error")
        
        parsed_data = {"raw_query": "Find AI image tools", "intent": "search", "entities": ["AI", "image"]}
        result = await processor._extract_ai_tools_data(parsed_data)
        
        assert result["tool_type"] == "image generation"  # Fallback based on keywords
        assert result["use_case"] == "general purpose"
    
    @pytest.mark.asyncio
    async def test_extract_mutual_funds_data_success(self, mock_gemini_client, processor):
        """Test successful mutual funds data extraction."""
        mock_gemini_client.generate_content.return_value = Mock(
            text='{"investment_type": "equity", "risk_level": "high", "time_horizon": "long-term", "amount_range": "medium", "investment_goal": "wealth creation"}'
        )
        
        parsed_data = {"raw_query": "Find equity mutual funds", "intent": "search", "entities": ["equity", "mutual funds"]}
        result = await processor._extract_mutual_funds_data(parsed_data)
        
        assert result["investment_type"] == "equity"
        assert result["risk_level"] == "high"
        assert result["time_horizon"] == "long-term"
    
    @pytest.mark.asyncio
    async def test_extract_mutual_funds_data_failure_fallback(self, mock_gemini_client, processor):
        """Test mutual funds data extraction failure with fallback."""
        mock_gemini_client.generate_content.side_effect = Exception("API Error")
        
        parsed_data = {"raw_query": "Find equity mutual funds", "intent": "search", "entities": ["equity", "mutual funds"]}
        result = await processor._extract_mutual_funds_data(parsed_data)
        
        assert result["investment_type"] == "equity"  # Fallback based on keywords
        assert result["risk_level"] == "medium"


class TestSchemas:
    """Test cases for Pydantic schemas."""
    
    def test_query_category_enum(self):
        """Test QueryCategory enum values."""
        assert QueryCategory.AI_TOOLS == "ai_tools"
        assert QueryCategory.MUTUAL_FUNDS == "mutual_funds"
        assert QueryCategory.GENERAL == "general"
        assert QueryCategory.UNKNOWN == "unknown"
    
    def test_base_query_result_validation(self):
        """Test BaseQueryResult validation."""
        # Valid data
        result = BaseQueryResult(
            query_text="Test query",
            confidence_score=0.8,
            processing_time=1.0,
            category=QueryCategory.AI_TOOLS
        )
        
        assert result.query_text == "Test query"
        assert result.confidence_score == 0.8
        assert result.processing_time == 1.0
        assert result.category == QueryCategory.AI_TOOLS
        
        # Invalid confidence score
        with pytest.raises(ValueError):
            BaseQueryResult(
                query_text="Test query",
                confidence_score=1.5,  # Invalid: > 1.0
                processing_time=1.0,
                category=QueryCategory.AI_TOOLS
            )
    
    def test_parsed_query_creation(self):
        """Test ParsedQuery creation."""
        base_result = BaseQueryResult(
            query_text="Test query",
            confidence_score=0.8,
            processing_time=1.0,
            category=QueryCategory.AI_TOOLS
        )
        
        result = ParsedQuery(
            base_result=base_result,
            suggestions=["Test suggestion"]
        )
        
        assert result.base_result == base_result
        assert result.suggestions == ["Test suggestion"]
        assert result.ai_tools_data is None
        assert result.mutual_funds_data is None
        assert result.general_data is None


class TestConfiguration:
    """Test cases for configuration validation."""
    
    def test_confidence_threshold_validation(self):
        """Test confidence threshold validation."""
        # Valid values
        valid_settings = Settings(agent_confidence_threshold=0.5)
        assert valid_settings.agent_confidence_threshold == 0.5
        
        valid_settings = Settings(agent_confidence_threshold=1.0)
        assert valid_settings.agent_confidence_threshold == 1.0
        
        valid_settings = Settings(agent_confidence_threshold=0.0)
        assert valid_settings.agent_confidence_threshold == 0.0
        
        # Invalid values
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            Settings(agent_confidence_threshold=1.5)
        
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            Settings(agent_confidence_threshold=-0.1)
    
    def test_agent_timeout_configuration(self):
        """Test agent-specific timeout configuration."""
        settings = Settings()
        
        assert settings.parser_timeout_seconds == 45
        assert settings.categorizer_timeout_seconds == 30
        assert settings.processor_timeout_seconds == 60
        assert settings.agent_timeout_seconds == 30  # Default


class TestErrorScenarios:
    """Test cases for error scenarios and edge cases."""
    
    @pytest.fixture
    def mock_gemini_client(self):
        """Mock Gemini client for error scenario tests."""
        client = Mock()
        client.generate_content = AsyncMock()
        return client
    
    @pytest.mark.asyncio
    async def test_parser_timeout_handling(self, mock_gemini_client):
        """Test parser timeout handling."""
        parser = NaturalLanguageParser(mock_gemini_client)
        
        # Mock a slow response that would timeout
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate slow processing
            return {"intent": "test", "entities": [], "domain": "test", "confidence": 0.8}
        
        parser.execute = slow_execute
        
        # Test with a safer timeout threshold
        with pytest.raises(asyncio.TimeoutError):
            await parser.execute_with_timeout("test query", timeout_seconds=0.05)
    
    @pytest.mark.asyncio
    async def test_categorizer_timeout_handling(self, mock_gemini_client):
        """Test categorizer timeout handling."""
        categorizer = DomainCategorizer(mock_gemini_client)
        
        # Mock a slow response that would timeout
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate slow processing
            return QueryCategory.GENERAL, 0.5
        
        categorizer.execute = slow_execute
        
        # Test with a safer timeout threshold
        with pytest.raises(asyncio.TimeoutError):
            await categorizer.execute_with_timeout({"raw_query": "test"}, timeout_seconds=0.05)
    
    @pytest.mark.asyncio
    async def test_processor_timeout_handling(self, mock_gemini_client):
        """Test processor timeout handling."""
        processor = QueryProcessor(mock_gemini_client)
        
        # Mock a slow response that would timeout
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate slow processing
            return ParsedQuery(
                base_result=BaseQueryResult(
                    query_text="test",
                    confidence_score=0.8,
                    processing_time=1.0,
                    category=QueryCategory.GENERAL
                )
            )
        
        processor.execute = slow_execute
        
        # Test with a safer timeout threshold
        with pytest.raises(asyncio.TimeoutError):
            await processor.execute_with_timeout("test query", timeout_seconds=0.05)
    
    @pytest.mark.asyncio
    async def test_gemini_api_failure_handling(self, mock_gemini_client):
        """Test handling of Gemini API failures."""
        # Mock API failure
        mock_gemini_client.generate_content.side_effect = Exception("API Rate Limit Exceeded")
        
        parser = NaturalLanguageParser(mock_gemini_client)
        
        with pytest.raises(Exception, match="API Rate Limit Exceeded"):
            await parser.execute("test query")
    
    @pytest.mark.asyncio
    async def test_malformed_json_response_handling(self, mock_gemini_client):
        """Test handling of malformed JSON responses from Gemini."""
        # Mock malformed JSON response
        mock_gemini_client.generate_content.return_value = Mock(
            text='{"intent": "search", "entities": ["AI", "tools", "domain": "ai_tools"}'  # Missing closing brace
        )
        
        parser = NaturalLanguageParser(mock_gemini_client)
        result = await parser.execute("Find AI tools")
        
        # Should use fallback parsing
        assert result["domain"] == "ai_tools"
        assert result["confidence"] == 0.3
        assert "Fallback parsing used" in result["additional_context"]
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, mock_gemini_client):
        """Test handling of network errors."""
        # Mock network error
        mock_gemini_client.generate_content.side_effect = ConnectionError("Network timeout")
        
        parser = NaturalLanguageParser(mock_gemini_client)
        
        with pytest.raises(ConnectionError, match="Network timeout"):
            await parser.execute("test query")
    
    @pytest.mark.asyncio
    async def test_large_response_handling(self, mock_gemini_client):
        """Test handling of very large responses."""
        # Mock very large response
        large_data = {"data": "x" * 20000}  # 20KB response
        mock_gemini_client.generate_content.return_value = Mock(
            text=json.dumps(large_data)
        )
        
        parser = NaturalLanguageParser(mock_gemini_client)
        result = await parser.execute("test query")
        
        # Should use fallback due to size limit
        assert result["domain"] == "general"
        assert result["confidence"] == 0.3


# Integration tests
class TestIntegration:
    """Integration tests for the complete workflow."""
    
    @pytest.fixture
    def mock_gemini_client(self):
        """Mock Gemini client for integration tests."""
        client = Mock()
        client.generate_content = AsyncMock()
        return client
    
    @pytest.mark.asyncio
    async def test_complete_query_processing_workflow(self, mock_gemini_client):
        """Test the complete query processing workflow."""
        # Mock Gemini responses with high confidence to avoid fallback
        mock_gemini_client.generate_content.side_effect = [
            Mock(text='{"intent": "search", "entities": ["AI", "tools"], "domain": "ai_tools", "confidence": 0.95}'),
            Mock(text='{"category": "ai_tools", "confidence": 0.95, "reasoning": "AI tools query"}'),
            Mock(text='{"tool_type": "image generation", "use_case": "creative design", "features_required": ["high resolution"], "budget_range": "medium", "technical_expertise": "beginner"}')
        ]
        
        processor = QueryProcessor(mock_gemini_client)
        
        # Process a query
        result = await processor.process_query("Find AI tools for image generation")
        
        # Verify the result
        assert isinstance(result, ParsedQuery)
        assert result.base_result.category == QueryCategory.AI_TOOLS
        assert result.base_result.confidence_score > 0.0
        assert result.ai_tools_data is not None
        assert result.ai_tools_data.tool_type == "image generation"
        assert len(result.suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_integration_with_error_recovery(self, mock_gemini_client):
        """Test integration workflow with error recovery."""
        # Mock first call success, second call failure
        mock_gemini_client.generate_content.side_effect = [
            Mock(text='{"intent": "search", "entities": ["mutual", "funds"], "domain": "mutual_funds", "confidence": 0.95}'),
            Mock(text='{"category": "mutual_funds", "confidence": 0.95, "reasoning": "Mutual funds query"}'),
            Exception("API Error")  # Third call fails (AI tools data extraction)
        ]
        
        processor = QueryProcessor(mock_gemini_client)
        
        # Process a query
        result = await processor.process_query("Find mutual funds for investment")
        
        # Should still complete with fallback data
        assert isinstance(result, ParsedQuery)
        assert result.base_result.category == QueryCategory.MUTUAL_FUNDS
        assert result.mutual_funds_data is not None
        # Should use fallback data due to API failure
        assert result.mutual_funds_data.investment_type == "equity"


if __name__ == "__main__":
    pytest.main([__file__])
