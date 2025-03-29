"""
GCC Web Scraper Source for Airbyte.
"""
import json
import os
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

import requests
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream
from airbyte_cdk.sources.streams.http.auth import TokenAuthenticator

from crawl4ai import Crawler


class WebPageStream(HttpStream):
    """
    Web page extraction stream using Crawl4AI.
    """
    
    url_base = "placeholder"  # Not used with Crawl4AI
    
    def __init__(self, config: Dict[str, Any], **kwargs):
        self.config = config
        self.crawler = Crawler(
            headless=True,
            stealth_mode=True,
            api_key=os.environ.get("CRAWL4AI_API_KEY", "")
        )
        # Initialize with a dummy authenticator as it's not used
        super().__init__(authenticator=TokenAuthenticator("dummy"))
    
    def next_page_token(
        self, response: requests.Response
    ) -> Optional[Mapping[str, Any]]:
        """No pagination for crawl4ai implementation."""
        return None
    
    def path(
        self, stream_state: Mapping[str, Any] = None, 
        stream_slice: Mapping[str, Any] = None, 
        next_page_token: Mapping[str, Any] = None
    ) -> str:
        """Not used with Crawl4AI."""
        return ""
    
    def parse_response(
        self, response: requests.Response, 
        stream_state: Mapping[str, Any], 
        stream_slice: Mapping[str, Any] = None, 
        next_page_token: Mapping[str, Any] = None
    ) -> Iterable[Mapping]:
        """Parse Crawl4AI crawler response."""
        if stream_slice and "url" in stream_slice:
            url = stream_slice["url"]
            try:
                # Use Crawl4AI to extract content
                result = self.crawler.scrape(url)
                if result:
                    yield {
                        "url": url,
                        "title": result.get("title", ""),
                        "body": result.get("content", ""),
                        "timestamp": result.get("timestamp", ""),
                        "metadata": result.get("metadata", {})
                    }
            except Exception as e:
                self.logger.error(f"Error scraping URL {url}: {str(e)}")
    
    def read_records(
        self, stream_state: Mapping[str, Any] = None, 
        stream_slice: Mapping[str, Any] = None, 
        next_page_token: Mapping[str, Any] = None
    ) -> Iterable[Mapping[str, Any]]:
        """Web crawling not easily compatible with HTTP semantics - override."""
        urls = self.config.get("urls", [])
        for url in urls:
            slice_config = {"url": url}
            for record in self.parse_response(None, stream_state, slice_config, None):
                yield record


class GCCWebScraperSource(AbstractSource):
    """Source for scraping web content from GCC websites."""
    
    def check_connection(self, logger, config) -> Tuple[bool, any]:
        """Check validity of the connector config."""
        if not config.get("urls"):
            return False, "URLs list cannot be empty."
        return True, None
    
    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        """Return available streams."""
        return [WebPageStream(config=config)] 