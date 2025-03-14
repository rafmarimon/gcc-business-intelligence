import os
import logging
from dotenv import load_dotenv
from src.utils.openai_utils import OpenAIClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_backoff_strategy():
    """Test the exponential backoff strategy with the OpenAI API."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        logger.error("No OpenAI API key found in environment variables")
        return
    
    logger.info(f"Using API key: {api_key[:5]}...{api_key[-4:]}")
    
    # Initialize our client with backoff logic
    client = OpenAIClient(api_key)
    
    try:
        # Test a simple completion
        logger.info("Testing chat completion with exponential backoff...")
        
        response = client.create_chat_completion(
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
    except Exception as e:
        logger.error(f"Error even with backoff: {e}")
        logger.error(f"Error type: {type(e)}")
        return False

if __name__ == "__main__":
    success = test_backoff_strategy()
    if success:
        logger.info("OpenAI API call with backoff was successful!")
    else:
        logger.info("OpenAI API call failed even with backoff strategy. You may need to wait longer or check your API key.") 