# Handling OpenAI API Rate Limits

This document explains how rate limits work with the OpenAI API and how they're handled in this project.

## Understanding Rate Limits

When using the OpenAI API, you may encounter `429: Too Many Requests` errors, which indicate that you've hit your rate limit. Rate limits are enforced based on:

1. **Requests per minute (RPM)**: Maximum number of API requests allowed per minute.
2. **Tokens per minute (TPM)**: Maximum number of tokens (input + output) that can be processed per minute.

Project-specific API keys (starting with `sk-proj--`) often have lower rate limits compared to organization-wide keys.

## Our Solution: Exponential Backoff

We've implemented an exponential backoff strategy to handle rate limit errors gracefully. When a rate limit is hit, the system:

1. Waits for a short period
2. Retries the request
3. If another rate limit occurs, increases the wait time exponentially
4. Continues until successful or until a maximum retry count is reached

This approach helps distribute requests over time and prevents continuous failed requests that would consume your quota.

## Implementation Details

### The OpenAI Client Wrapper

We've created a wrapper around the OpenAI client in `src/utils/openai_utils.py` that implements exponential backoff:

```python
def with_exponential_backoff(func):
    """Decorator that implements exponential backoff for OpenAI API calls."""
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
```

The `OpenAIClient` class wraps the standard OpenAI client and applies this backoff strategy to all API calls.

### Usage in the Project

To use the client with exponential backoff:

```python
from src.utils.openai_utils import OpenAIClient

# Initialize the client
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAIClient(api_key)

# Make API calls with automatic backoff
response = client.create_chat_completion(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Write a short summary."}
    ],
    max_tokens=150
)
```

## Other Recommendations

If you continue to experience rate limit issues:

1. **Increase your usage tier**: Check the limits section of your OpenAI account settings.
2. **Use batch processing**: Group similar requests together to minimize API calls.
3. **Implement caching**: Store common responses to avoid redundant API calls.
4. **Consider using an organization API key**: These typically have higher limits than project-specific keys.

## Testing

You can test the exponential backoff implementation by running:

```bash
python test_backoff.py
```

This script will attempt to make an API call with our backoff-enabled client, demonstrating how it handles any rate limits encountered. 