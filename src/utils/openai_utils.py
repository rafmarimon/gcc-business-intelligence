import time
import random
import logging
import os
from openai import OpenAI
from openai import RateLimitError, APIError, APIConnectionError, AuthenticationError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

def with_exponential_backoff(func):
    """
    Decorator that implements exponential backoff for OpenAI API calls.
    
    Args:
        func: The function to decorate.
        
    Returns:
        The decorated function.
    """
    def wrapper(*args, **kwargs):
        max_retries = 5
        base_delay = 1  # Start with a 1-second delay
        
        retries = 0
        while True:
            try:
                return func(*args, **kwargs)
            except (RateLimitError, APIError, APIConnectionError) as e:
                retries += 1
                
                if retries > max_retries:
                    logger.error(f"Maximum retries ({max_retries}) exceeded. Giving up.")
                    raise
                
                # Calculate delay with exponential backoff and jitter
                delay = base_delay * (2 ** (retries - 1)) + random.uniform(0, 0.1)
                
                error_code = "429" if "429" in str(e) else "API error"
                logger.warning(f"Received {error_code} from OpenAI. Retrying in {delay:.2f} seconds... (Attempt {retries}/{max_retries})")
                time.sleep(delay)
            except AuthenticationError as e:
                logger.error(f"Authentication error: {str(e)}")
                logger.error("Please check your OpenAI API key in the .env file.")
                raise
            except Exception as e:
                # For other exceptions, don't retry
                logger.error(f"Unexpected error: {str(e)}")
                raise
    
    return wrapper

class OpenAIClient:
    """
    A wrapper around the OpenAI client that implements exponential backoff and model fallback.
    """
    def __init__(self, api_key=None):
        # Use provided key or get from environment
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not provided and not found in environment variables")
            
        # Get model configuration from environment or use defaults
        self.primary_model = os.getenv('OPENAI_PRIMARY_MODEL', 'gpt-4o')
        self.fallback_model = os.getenv('OPENAI_FALLBACK_MODEL', 'gpt-3.5-turbo')
        self.default_temperature = float(os.getenv('OPENAI_TEMPERATURE', '0.3'))
        
        # Initialize the client
        self.client = OpenAI(api_key=self.api_key)
        
        logger.info(f"OpenAI client initialized. Primary model: {self.primary_model}")
    
    @with_exponential_backoff
    def create_chat_completion(self, model=None, messages=None, temperature=None, use_fallback=True, **kwargs):
        """
        Create a chat completion with exponential backoff and model fallback.
        
        Args:
            model: The model to use (defaults to primary model from env)
            messages: The messages to send
            temperature: The temperature to use
            use_fallback: Whether to try the fallback model if the primary fails
            **kwargs: Additional arguments to pass to the API
            
        Returns:
            The API response
        """
        if not messages:
            raise ValueError("Messages are required for chat completion")
            
        # Use provided values or defaults
        model = model or self.primary_model
        temperature = temperature if temperature is not None else self.default_temperature
        
        try:
            return self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                **kwargs
            )
        except Exception as e:
            # If using the primary model and fallback is enabled, try the fallback model
            if use_fallback and model == self.primary_model:
                logger.warning(f"Error with {model}: {str(e)}. Trying fallback model {self.fallback_model}")
                return self.create_chat_completion(
                    model=self.fallback_model,
                    messages=messages,
                    temperature=temperature,
                    use_fallback=False,  # Prevent infinite recursion
                    **kwargs
                )
            else:
                # If already using fallback or fallback disabled, re-raise the exception
                raise
    
    @with_exponential_backoff
    def create_embedding(self, model="text-embedding-ada-002", input=None, **kwargs):
        """
        Create embeddings with exponential backoff.
        
        Args:
            model: The model to use.
            input: The input to embed.
            **kwargs: Additional arguments to pass to the API.
            
        Returns:
            The API response.
        """
        if not input:
            raise ValueError("Input is required for embedding creation")
            
        return self.client.embeddings.create(
            model=model,
            input=input,
            **kwargs
        )
        
    def verify_connection(self):
        """
        Verify that the OpenAI API connection is working.
        
        Returns:
            tuple: (success, message)
        """
        try:
            # Simple test request
            response = self.create_chat_completion(
                messages=[{"role": "user", "content": "Hello, this is a test."}],
                max_tokens=20,
                use_fallback=True
            )
            model_used = response.model
            return True, f"Connection successful using model: {model_used}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}" 