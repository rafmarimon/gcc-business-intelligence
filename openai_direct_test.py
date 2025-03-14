import requests
import sys

def test_api_key(api_key):
    """Test if the OpenAI API key is valid and functioning."""
    print(f"Testing API key: {api_key[:5]}...{api_key[-4:] if len(api_key) > 8 else '***'}")
    
    # Test basic API access
    try:
        print("\nChecking available models...")
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        response = requests.get("https://api.openai.com/v1/models", headers=headers)
        
        if response.status_code == 200:
            models = response.json()['data']
            print(f"✅ Success! Found {len(models)} available models.")
            return True
        else:
            print(f"❌ Failed with status code {response.status_code}")
            print(response.text)
            return False
    
    except Exception as e:
        print(f"❌ Exception occurred: {str(e)}")
        return False

def main():
    """Get API key from user and test it."""
    if len(sys.argv) > 1:
        # Get API key from command line argument
        api_key = sys.argv[1]
    else:
        # Get API key from user input
        api_key = input("Enter your OpenAI API key: ").strip()
    
    if not api_key:
        print("No API key provided. Exiting.")
        return
    
    test_api_key(api_key)

if __name__ == "__main__":
    main() 