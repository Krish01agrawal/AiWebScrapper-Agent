"""
Gemini API client setup following Google's recommended patterns.
"""
import logging
from typing import Optional, Dict, Any
import google.generativeai as genai
from .config import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Wrapper class for Gemini GenerativeModel to provide consistent interface for agents."""
    
    def __init__(self, model_name: str = 'gemini-1.5-pro'):
        """Initialize the Gemini client with a specific model."""
        self.model_name = model_name
        self._model: Optional[genai.GenerativeModel] = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the underlying Gemini model."""
        try:
            if not settings.gemini_api_key:
                logger.warning("Gemini API key not provided. AI functionality will be disabled.")
                return
            
            # Basic API key format validation
            if len(settings.gemini_api_key) < 20:
                logger.error("Gemini API key appears to be too short. Please check your configuration.")
                return
                
            # Configure the API key
            genai.configure(api_key=settings.gemini_api_key)
            
            # Create the model instance
            self._model = genai.GenerativeModel(self.model_name)
            logger.info(f"Gemini client initialized successfully with model: {self.model_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            if "API key" in str(e).lower():
                logger.error("Invalid or expired Gemini API key. Please check your configuration.")
            elif "quota" in str(e).lower():
                logger.error("Gemini API quota exceeded. Please check your billing status.")
            elif "network" in str(e).lower() or "connection" in str(e).lower():
                logger.error("Network connectivity issue. Please check your internet connection.")
            else:
                logger.error("Unknown error during Gemini client initialization.")
    
    async def generate_content(
        self, 
        prompt: str, 
        generation_config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Generate content using the Gemini model."""
        if not self._model:
            raise RuntimeError("Gemini model not initialized. Check your API key configuration.")
        
        try:
            # Set default generation config if none provided
            if generation_config is None:
                generation_config = {
                    "temperature": getattr(settings, 'gemini_temperature', 0.7),
                    "max_output_tokens": getattr(settings, 'gemini_max_tokens', 1000),
                }
            
            # Generate content
            response = self._model.generate_content(prompt, generation_config=generation_config)
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate content: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if the Gemini client is available and ready."""
        return self._model is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            "model_name": self.model_name,
            "is_available": self.is_available(),
            "api_key_configured": bool(settings.gemini_api_key)
        }


def init_gemini_client() -> Optional[genai.GenerativeModel]:
    """Initialize Gemini client using API key from environment."""
    try:
        # Check if API key is provided
        if not settings.gemini_api_key:
            logger.warning("Gemini API key not provided. AI functionality will be disabled.")
            return None
        
        # Basic API key format validation (Google API keys are typically 39 characters)
        if len(settings.gemini_api_key) < 20:
            logger.error("Gemini API key appears to be too short. Please check your configuration.")
            return None
            
        # Configure the API key
        genai.configure(api_key=settings.gemini_api_key)
        
        # Create the model instance
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Initialize client without blocking API test during startup
        logger.info("Gemini client initialized successfully")
        
        return model
            
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {e}")
        if "API key" in str(e).lower():
            logger.error("Invalid or expired Gemini API key. Please check your configuration.")
        elif "quota" in str(e).lower():
            logger.error("Gemini API quota exceeded. Please check your billing status.")
        elif "network" in str(e).lower() or "connection" in str(e).lower():
            logger.error("Network connectivity issue. Please check your internet connection.")
        else:
            logger.error("Unknown error during Gemini client initialization.")
        return None


def get_gemini_model() -> Optional[genai.GenerativeModel]:
    """Get the Gemini model instance."""
    try:
        return genai.GenerativeModel('gemini-1.5-pro')
    except Exception as e:
        logger.error(f"Failed to get Gemini model: {e}")
        return None


async def test_gemini_connection() -> bool:
    """Test Gemini API connectivity."""
    try:
        model = get_gemini_model()
        if model:
            response = model.generate_content("Test connection")
            return response is not None
        return False
    except Exception as e:
        logger.error(f"Gemini connection test failed: {e}")
        return False
