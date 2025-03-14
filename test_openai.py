import os
import openai
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_openai_connection():
    """Test if the OpenAI API is working with current credentials."""
    print("Testing OpenAI API connection...")
    
    # Get the API key from environment variables
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("ERROR: No OpenAI API key found in .env file.")
        return False
    
    # Mask the API key for display (showing only first 5 and last 4 characters)
    masked_key = api_key[:5] + "..." + api_key[-4:] if len(api_key) > 9 else "***"
    print(f"Using API key: {masked_key}")
    
    # Method 1: OpenAI Python client
    try:
        print("\nAttempting connection using OpenAI Python client...")
        openai.api_key = api_key
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'OpenAI connection successful' if you can read this."}
            ],
            max_tokens=20
        )
        
        print("API Response:")
        print(response.choices[0].message.content)
        print("✅ Method 1 successful!")
        
    except Exception as e:
        print(f"❌ Method 1 failed: {str(e)}")
    
    # Method 2: Direct API call with requests
    try:
        print("\nAttempting connection using direct API call...")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Direct API call successful' if you can read this."}
            ],
            "max_tokens": 20
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print("API Response:")
            print(content)
            print("✅ Method 2 successful!")
        else:
            print(f"❌ Method 2 failed with status code {response.status_code}:")
            print(response.text)
    
    except Exception as e:
        print(f"❌ Method 2 failed: {str(e)}")
    
    # Test API key validity
    try:
        print("\nChecking API key validity via models endpoint...")
        
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        response = requests.get("https://api.openai.com/v1/models", headers=headers)
        
        if response.status_code == 200:
            print("✅ API key is valid! Available models:")
            models = response.json()['data']
            for model in models[:5]:  # Show only first 5 models
                print(f"- {model['id']}")
            if len(models) > 5:
                print(f"... and {len(models) - 5} more")
        else:
            print(f"❌ API key validation failed with status code {response.status_code}:")
            print(response.text)
    
    except Exception as e:
        print(f"❌ API key validation failed: {str(e)}")

if __name__ == "__main__":
    test_openai_connection() 