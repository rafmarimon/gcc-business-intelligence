import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, BrowserConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
import json

async def test_crawl4ai():
    # Create a web scraping strategy
    scraping_strategy = LXMLWebScrapingStrategy()
    
    # Create an extraction strategy with the specific selectors for Gulf News
    extraction_rules = {
        "baseSelector": ".story-block-container",
        "fields": {
            "headline": {
                "selector": ".story-block-title h3 a",
                "type": "text"
            },
            "summary": {
                "selector": ".story-block-teaser",
                "type": "text"
            },
            "link": {
                "selector": ".story-block-title h3 a",
                "type": "attribute",
                "attribute": "href"
            },
            "date": {
                "selector": ".story-block-byline time",
                "type": "text"
            }
        }
    }
    extraction_strategy = JsonCssExtractionStrategy(extraction_rules)
    
    # Configure the crawler run
    config = CrawlerRunConfig(
        extraction_strategy=extraction_strategy,
        scraping_strategy=scraping_strategy,
        cache_mode=CacheMode.BYPASS,  # Don't use cache
        check_robots_txt=True,  # Respect robots.txt
        verbose=True
    )
    
    # Create a browser config
    browser_config = BrowserConfig(headless=True)
    
    # Run the crawler
    url = "https://gulfnews.com/business"
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=config)
        
        # Print information about the result
        print(f"Success: {result.success}")
        if result.success:
            print(f"Page title: {result.page_title if hasattr(result, 'page_title') else 'N/A'}")
            print(f"Extracted content available: {result.extracted_content is not None}")
            
            if result.extracted_content:
                try:
                    # Parse and print extracted content
                    articles = json.loads(result.extracted_content)
                    # The content is a list of articles directly
                    print(f"Found {len(articles)} articles")
                    
                    # Print first 3 article headlines if available
                    for i, article in enumerate(articles[:3]):
                        print(f"Article {i+1}: {article.get('headline', 'No headline')}")
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON: {e}")
                    print(f"Raw content: {result.extracted_content[:200]}...")
        else:
            print(f"Error: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(test_crawl4ai()) 