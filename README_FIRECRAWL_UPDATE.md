# Firecrawl Integration Guide

This guide explains how to use Firecrawl for web scraping in two different ways:
1. Using the direct REST API (our custom implementation)
2. Using the official Firecrawl SDK (recommended)

## Getting Started

### Prerequisites

- Python 3.8+
- A valid Firecrawl API key (sign up at [firecrawl.dev](https://firecrawl.dev/))

### Installation

1. Clone this repository
2. Install the required dependencies:

```bash
# For direct API implementation
pip install requests beautifulsoup4 python-dotenv

# For SDK implementation
pip install firecrawl-py pydantic
```

3. Set up your Firecrawl API key in the `.env` file:

```
FIRECRAWL_API_KEY=your_actual_api_key_here
```

## Why You're Not Getting Results

If you're encountering issues with the scripts not returning data, there are several possible reasons:

1. **Invalid API Key**: The most common issue. Your API key must be in the format `fc-xxxxxxxxx`. Make sure you've signed up at [firecrawl.dev](https://firecrawl.dev/) and replaced the placeholder in the `.env` file.

2. **401 Unauthorized Errors**: This indicates authentication problems with your API key.

3. **Rate Limiting**: Firecrawl might limit the number of requests based on your subscription plan.

4. **Site Blocking**: Some websites actively block scraping attempts.

## Using the Direct API Method

Our custom implementation uses direct REST API calls to Firecrawl. While functional, it lacks some features of the official SDK:

```python
from firecrawl_collector import FirecrawlNewsCollector

# Initialize with a config file
collector = FirecrawlNewsCollector(config_file="config/firecrawl_sources.json")

# Collect news with specific keywords
articles = collector.collect_news(keywords=["UAE economy", "Dubai business"])
```

This approach is useful for understanding how the API works, but the official SDK offers better integration.

## Using the Official Firecrawl SDK (Recommended)

The Firecrawl SDK provides more robust features and easier integration:

```python
from firecrawl import FirecrawlApp

# Initialize the Firecrawl app
app = FirecrawlApp(api_key="your_firecrawl_api_key")

# Scrape a URL
result = app.scrape_url('https://example.com', params={
    'formats': ['markdown', 'html']
})

# Extract structured data with Pydantic
from pydantic import BaseModel, Field
from typing import List

class ArticleSchema(BaseModel):
    title: str
    content: str

class NewsCollection(BaseModel):
    articles: List[ArticleSchema] = Field(..., description="List of news articles")

result = app.scrape_url('https://example.com', {
    'formats': ['json'],
    'jsonOptions': {
        'schema': NewsCollection.model_json_schema(),
    }
})

# Crawl an entire website
crawl_status = app.crawl_url(
    'https://example.com', 
    params={
        'limit': 10,
        'scrapeOptions': {'formats': ['markdown']}
    },
    poll_interval=30
)
```

## SDK vs Direct API: Key Differences

| Feature | SDK | Direct API |
|---------|-----|------------|
| Ease of use | ✅ Simple, high-level methods | 🔶 Requires more code |
| Error handling | ✅ Built-in | 🔶 Manual implementation |
| Type safety | ✅ With Pydantic | 🔶 Manual validation |
| Documentation | ✅ Extensive | 🔶 Limited |
| Debugging | ✅ Better error messages | 🔶 Generic HTTP errors |
| Updates | ✅ Automatically maintained | 🔶 Requires manual updates |

## Advanced Features

Firecrawl offers several advanced features that might be useful:

### Page Interaction

Execute actions on the page before scraping:

```python
result = app.scrape_url('https://example.com', params={
    'formats': ['markdown'],
    'actions': [
        {"type": "wait", "milliseconds": 2000},
        {"type": "click", "selector": "button.load-more"},
        {"type": "wait", "milliseconds": 2000},
        {"type": "scrape"}
    ]
})
```

### LLM Extraction

Extract structured data using LLMs:

```python
result = app.scrape_url('https://example.com', {
    'formats': ['json'],
    'jsonOptions': {
        'prompt': "Extract all product prices and names from this page."
    }
})
```

### PDF and Document Parsing

Firecrawl can also extract content from PDFs and other documents:

```python
result = app.scrape_url('https://example.com/document.pdf', params={
    'formats': ['markdown']
})
```

## Troubleshooting

If you continue to experience issues:

1. **Check API Key**: Ensure your API key is valid and correctly formatted.
2. **Verify Account Status**: Check your Firecrawl account for any usage limitations.
3. **Test with Simple URL**: Try scraping a simple, publicly accessible website first.
4. **Check for JavaScript Requirements**: Some sites require JavaScript rendering.
5. **Monitor Rate Limits**: Be aware of your plan's rate limits.

## Additional Resources

- [Firecrawl Documentation](https://docs.firecrawl.dev/)
- [Firecrawl Python SDK](https://pypi.org/project/firecrawl-py/)
- [Firecrawl API Reference](https://docs.firecrawl.dev/api-reference/introduction)

## Support

For issues with the Firecrawl service, contact their support. For issues with our custom implementation, please open an issue in this repository. 