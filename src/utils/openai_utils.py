import time
import random
import logging
import os
import requests
from io import BytesIO
import openai
from openai import OpenAI
from openai import RateLimitError, APIError, APIConnectionError, AuthenticationError
from dotenv import load_dotenv
import base64

# Import our custom configuration
from src.utils.openai_config import configure_openai, create_openai_client

# Load environment variables
load_dotenv()

# Configure OpenAI globally
configure_openai()

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
    Utility class for interacting with OpenAI APIs.
    
    Provides methods for generating text, embeddings, and images using OpenAI models.
    Includes error handling, rate limiting management, and model fallback options.
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the OpenAI client with API key and model settings.
        
        Args:
            api_key: Optional OpenAI API key (will use environment variable if not provided)
        """
        # Use provided key or get from environment
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not provided and not found in environment variables")
            
        # Get model configuration from environment or use defaults
        self.primary_model = os.getenv('OPENAI_MODEL', 'gpt-4o')
        self.fallback_model = os.getenv('OPENAI_FALLBACK_MODEL', 'gpt-3.5-turbo')
        self.default_temperature = float(os.getenv('OPENAI_TEMPERATURE', '0.3'))
        
        # Get image generation settings
        self.image_model = os.getenv('DALLE_MODEL', 'dall-e-3')
        self.use_gpt4o_images = os.getenv('USE_GPT4O_IMAGES', 'true').lower() == 'true'
        
        # Create OpenAI client - FIXED initialization without proxies
        try:
            logger.info("Initializing OpenAI client with only API key")
            
            # Use our configuration utility instead of direct initialization
            self.client = create_openai_client(api_key=self.api_key)
            
            logger.info(f"OpenAI client initialized. Primary model: {self.primary_model}")
            
            if self.use_gpt4o_images:
                logger.info(f"GPT-4o image generation enabled. Will try GPT-4o first, falling back to DALL-E if needed.")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            raise
    
    @with_exponential_backoff
    def create_chat_completion(self, messages, model=None, temperature=None, max_tokens=None, **kwargs):
        """
        Create a chat completion with the OpenAI API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to primary model)
            temperature: Temperature for sampling (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            OpenAI API response object
        """
        if not messages:
            raise ValueError("Messages are required for chat completion")
            
        # Use provided values or defaults
        model = model or self.primary_model
        temperature = temperature if temperature is not None else self.default_temperature
        
        try:
            # Remove any proxy-related kwargs
            if 'proxies' in kwargs:
                del kwargs['proxies']
            
            completion_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
            
            # Add max_tokens if specified
            if max_tokens is not None:
                completion_params["max_tokens"] = max_tokens
                
            # Add any additional kwargs
            completion_params.update(kwargs)
            
            return self.client.chat.completions.create(**completion_params)
        except Exception as e:
            # If using the primary model, try fallback
            if model == self.primary_model:
                logger.warning(f"Error with {model}: {str(e)}. Trying fallback model {self.fallback_model}")
                return self.create_chat_completion(
                    messages=messages,
                    model=self.fallback_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            else:
                # If already using fallback, re-raise
                raise
                
    def generate_text(self, prompt, system_prompt=None, model=None, temperature=None, max_tokens=None):
        """
        Generate text using the OpenAI chat completion API.
        
        Args:
            prompt: User prompt to generate text from
            system_prompt: Optional system prompt to set context
            model: Model to use (defaults to primary model)
            temperature: Temperature for sampling (0-1)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text as a string
        """
        # Build messages array
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        # Add user prompt
        messages.append({"role": "user", "content": prompt})
        
        # Call chat completion API
        response = self.create_chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Extract and return the generated text
        if hasattr(response, 'choices') and len(response.choices) > 0:
            return response.choices[0].message.content
        
        return ""
    
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
        
        # Remove the proxies parameter which causes problems
        if 'proxies' in kwargs:
            del kwargs['proxies']
            
        return self.client.embeddings.create(
            model=model,
            input=input,
            **kwargs
        )
    
    @with_exponential_backoff
    def generate_image_with_gpt4o(self, prompt, save_path=None):
        """
        Generate an image using GPT-4o's image generation capabilities.
        
        Args:
            prompt: The text prompt to generate an image from
            save_path: Optional path to save the image
            
        Returns:
            If save_path is provided, returns the path to the saved image.
            Otherwise, returns the image URL or base64 data.
            Returns None if generation fails.
        
        Raises:
            Exception: If there's an API error or other issue
        """
        if not prompt:
            raise ValueError("Prompt is required for image generation")
        
        logger.info(f"Generating image with GPT-4o: {prompt[:50]}...")
        
        try:
            # Call GPT-4o with a vision system prompt
            messages = [
                {
                    "role": "system", 
                    "content": "You are a professional image creator specialized in business imagery for LinkedIn. Create professional, high-quality business images for LinkedIn posts."
                },
                {
                    "role": "user", 
                    "content": f"Create a professional image based on this description:\n\n{prompt}\n\nPlease generate the image directly."
                }
            ]
            
            # Request an image from GPT-4o
            response = self.client.chat.completions.create(
                model=self.primary_model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                response_format={"type": "image"}
            )
            
            # Extract image data from response
            if hasattr(response, 'choices') and len(response.choices) > 0 and hasattr(response.choices[0], 'message'):
                message = response.choices[0].message
                if hasattr(message, 'content') and message.content.startswith('data:image'):
                    # It's a base64 image
                    image_data = message.content.split(',')[1]
                    
                    # Save the image if save_path is provided
                    if save_path:
                        try:
                            # Decode the base64 data
                            image_bytes = BytesIO(base64.b64decode(image_data))
                            
                            # Create the directory if it doesn't exist
                            os.makedirs(os.path.dirname(save_path), exist_ok=True)
                            
                            # Save the image
                            with open(save_path, 'wb') as f:
                                f.write(image_bytes.getvalue())
                                
                            logger.info(f"GPT-4o generated image saved to {save_path}")
                            return save_path
                        except Exception as e:
                            logger.error(f"Error saving GPT-4o image: {str(e)}")
                            return message.content  # Return the base64 data
                    
                    return message.content  # Return the base64 data
                else:
                    logger.warning(f"GPT-4o did not return an image, got: {message.content[:100]}")
                    return None
            
            logger.warning("GPT-4o response did not contain expected image data")
            return None
        
        except Exception as e:
            logger.error(f"Error generating image with GPT-4o: {str(e)}")
            raise
    
    @with_exponential_backoff
    def generate_image_with_dalle(self, prompt, model="dall-e-3", size="1024x1024", quality="standard", style="natural", n=1, save_path=None):
        """
        Generate an image using DALL-E with exponential backoff.
        
        Args:
            prompt: The text prompt to generate an image from
            model: The DALL-E model to use (default: dall-e-3)
            size: Image size (1024x1024, 1792x1024, or 1024x1792)
            quality: Image quality (standard or hd)
            style: Image style (natural or vivid)
            n: Number of images to generate
            save_path: Optional path to save the image
            
        Returns:
            If save_path is provided, returns the path to the saved image.
            Otherwise, returns the image URL from the API.
        """
        if not prompt:
            raise ValueError("Prompt is required for image generation")
        
        logger.info(f"Generating image with DALL-E: {prompt[:50]}...")
        
        try:
            response = self.client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                quality=quality,
                style=style,
                n=n
            )
            
            # Get the image URL from the response
            image_url = response.data[0].url
            
            # If save_path is provided, download and save the image
            if save_path:
                try:
                    # Download the image
                    image_response = requests.get(image_url)
                    image_response.raise_for_status()
                    
                    # Create the directory if it doesn't exist
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    
                    # Save the image
                    with open(save_path, 'wb') as f:
                        f.write(image_response.content)
                        
                    logger.info(f"DALL-E image saved to {save_path}")
                    return save_path
                except Exception as e:
                    logger.error(f"Error saving DALL-E image: {str(e)}")
                    return image_url
            
            return image_url
        
        except Exception as e:
            logger.error(f"Error generating image with DALL-E: {str(e)}")
            raise
    
    def generate_image(self, prompt, size="1024x1024", quality="standard", style="natural", model="dall-e-3", n=1, save_path=None):
        """
        Generate an image using GPT-4o first (if enabled), falling back to DALL-E if needed.
        
        Args:
            prompt: The text prompt to generate an image from
            size: Image size (for DALL-E)
            quality: Image quality (for DALL-E)
            style: Image style (for DALL-E)
            model: The DALL-E model to use if fallback is needed
            n: Number of images to generate (for DALL-E)
            save_path: Optional path to save the image
            
        Returns:
            If save_path is provided, returns the path to the saved image.
            Otherwise, returns the image URL or data.
            Returns None if all generation attempts fail.
            
        Additional fields in return metadata:
            image_generator: The model that generated the image ('gpt-4o' or 'dall-e')
        """
        image_generator = None
        
        try:
            # Try GPT-4o first if enabled
            if self.use_gpt4o_images:
                try:
                    logger.info("Attempting to generate image with GPT-4o...")
                    result = self.generate_image_with_gpt4o(prompt, save_path)
                    if result:
                        logger.info("Successfully generated image with GPT-4o")
                        return {
                            "result": result,
                            "image_generator": "gpt-4o"
                        }
                    else:
                        logger.warning("GPT-4o image generation did not produce a valid image, falling back to DALL-E")
                except Exception as e:
                    logger.warning(f"GPT-4o image generation failed: {str(e)}. Falling back to DALL-E.")
            
            # If GPT-4o is disabled or failed, use DALL-E
            logger.info("Generating image with DALL-E...")
            result = self.generate_image_with_dalle(
                prompt=prompt,
                model=model,
                size=size,
                quality=quality,
                style=style,
                n=n,
                save_path=save_path
            )
            
            return {
                "result": result,
                "image_generator": "dall-e"
            }
            
        except Exception as e:
            logger.error(f"All image generation methods failed: {str(e)}")
            return None
        
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