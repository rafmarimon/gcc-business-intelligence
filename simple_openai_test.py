import os
import json
import logging
import time
import requests
from dotenv import load_dotenv
from openai import OpenAI
from openai.error import RateLimitError, APIError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_api_quota(api_key):
    """Check the current API quota status."""
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        # Try to get the billing info to see our current usage
        response = requests.get(
            "https://api.openai.com/v1/usage",
            headers=headers
        )
        
        if response.status_code == 200:
            logger.info("Successfully retrieved usage information")
            logger.info(f"Response: {response.json()}")
            return True
        else:
            logger.error(f"Failed to get usage information: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error checking API quota: {e}")
        return False

def test_openai_generation():
    """Test OpenAI API connection and text generation."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        logger.error("No OpenAI API key found in environment variables")
        return
    
    logger.info(f"Using API key: {api_key[:5]}...{api_key[-4:]}")
    
    # Check API quota first
    logger.info("Checking API quota...")
    check_api_quota(api_key)
    
    try:
        client = OpenAI(api_key=api_key)
        logger.info("Successfully created OpenAI client")
        
        # Test a simple completion
        logger.info("Testing a simple completion...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Write a short summary about the UAE economy in 2023."}
            ],
            max_tokens=150
        )
        
        logger.info("Successfully received response from OpenAI")
        logger.info("Response content:")
        print(response.choices[0].message.content)
        
        return True
    except RateLimitError as e:
        logger.error(f"Rate limit exceeded: {e}")
        logger.error("Your API key may have reached its quota or rate limit.")
        logger.error("Try using a different API key or wait and try again later.")
        return False
    except APIError as e:
        logger.error(f"API error from OpenAI: {e}")
        if "429" in str(e):
            logger.error("This is a rate limit error (429). Your API key may have reached its quota.")
            logger.error("Try using a different API key or wait and try again later.")
        return False
    except Exception as e:
        logger.error(f"Error connecting to OpenAI API: {e}")
        logger.error(f"Error type: {type(e)}")
        return False

if __name__ == "__main__":
    success = test_openai_generation()
    if success:
        logger.info("OpenAI API connection and generation test successful!")
    else:
        logger.error("OpenAI API test failed. Please check your API key, quota limits, and internet connection.") 