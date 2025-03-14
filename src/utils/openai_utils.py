import time
import random
import logging
from openai import OpenAI
from openai import RateLimitError, APIError, APIConnectionError

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
            except Exception as e:
                # For other exceptions, don't retry
                logger.error(f"Unexpected error: {str(e)}")
                raise
    
    return wrapper

class OpenAIClient:
    """
    A wrapper around the OpenAI client that implements exponential backoff.
    """
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
    
    @with_exponential_backoff
    def create_chat_completion(self, model, messages, **kwargs):
        """
        Create a chat completion with exponential backoff.
        
        Args:
            model: The model to use.
            messages: The messages to send.
            **kwargs: Additional arguments to pass to the API.
            
        Returns:
            The API response.
        """
        return self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
    
    @with_exponential_backoff
    def create_embedding(self, model, input, **kwargs):
        """
        Create embeddings with exponential backoff.
        
        Args:
            model: The model to use.
            input: The input to embed.
            **kwargs: Additional arguments to pass to the API.
            
        Returns:
            The API response.
        """
        return self.client.embeddings.create(
            model=model,
            input=input,
            **kwargs
        ) 