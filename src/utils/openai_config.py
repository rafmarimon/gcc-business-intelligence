"""
Global OpenAI Configuration Module

This module provides standardized configuration for OpenAI API access
throughout the application, ensuring consistent settings and avoiding
initialization errors related to proxy settings.
"""

import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

def configure_openai():
    """
    Configure the OpenAI module with consistent settings.
    This ensures proxy and other settings are applied consistently.
    
    Returns:
        None
    """
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.warning("OPENAI_API_KEY not found in environment variables")
    
    # Clear any proxy settings that might cause issues
    proxy_vars = ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]
    for var in proxy_vars:
        if var in os.environ:
            logger.info(f"Temporarily clearing {var} environment variable for OpenAI initialization")
            del os.environ[var]

def create_openai_client(api_key=None):
    """
    Create an OpenAI client with consistent settings.
    
    Args:
        api_key: Optional API key (uses environment variable if not provided)
        
    Returns:
        OpenAI: Initialized OpenAI client
    """
    # Use provided key or get from environment
    api_key = api_key or os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OpenAI API key not provided and not found in environment variables")
    
    # Clear proxy settings before initialization
    configure_openai()
    
    try:
        # Create client with minimal settings
        client = OpenAI(api_key=api_key)
        logger.debug("OpenAI client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {str(e)}")
        raise

# Configure on module import
configure_openai() 