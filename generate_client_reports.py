#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GCC-focused client report generator for Google and Nestle.
Retrieves articles from various sources and generates comprehensive reports.
"""

import os
import sys
import json
import logging
import argparse
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
import re

# Ensure proper import paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import related modules
try:
    from src.utils.openai_utils import OpenAIClient
    from src.utils.redis_cache import get_redis_cache, RedisCache
    from src.models.client_model import ClientModel
    from src.crawler import SimplifiedCrawler
except ImportError as e:
    print(f"Error importing required modules: {e}")
    # Try alternate import paths
    try:
        # If run from project root
        from src.utils.openai_utils import OpenAIClient as OpenAIUtil
        from src.utils.redis_cache import RedisCache
        from src.models.client_model import ClientModel
        from src.crawler import SimplifiedCrawler
    except ImportError as e2:
        print(f"Could not import modules with alternate paths: {e2}")
        print("Make sure you're running from the project root and have installed all requirements.")
        sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClientReportGenerator:
    """Generate specific client reports using real data from the past 7 days."""
    
    def __init__(self, reports_dir: str, lookback_days: int, simulate_crawling: bool):
        """Initialize the report generator with Redis connection and other dependencies."""
        logger.info("Initializing ClientReportGenerator")
        
        # Set up Redis connection
        self.redis_cache = RedisCache()
        
        # Initialize the crawler component
        self.crawler = SimplifiedCrawler()
        
        # Initialize client model
        self.client_model = ClientModel()
        
        # Initialize OpenAI for report generation
        self.openai_client = OpenAIClient()
        
        # Set up reports directory
        self.reports_dir = reports_dir
        if not os.path.exists(self.reports_dir):
            os.makedirs(self.reports_dir)
            logger.info(f"Created client reports directory at {self.reports_dir}")
        
        # Set lookback period (default 7 days)
        self.lookback_days = lookback_days
        
        # Set simulate_crawling attribute
        self.simulate_crawling = simulate_crawling
    
    def _create_specific_clients(self):
        """Create Google and Nestle clients if they don't exist."""
        # Check all existing clients
        all_clients = self.client_model.get_all_clients()
        client_names = [client.get('name', '') for client in all_clients]
        
        # Create Google client if it doesn't exist
        if 'Google' not in client_names:
            google_client = self.client_model.create_client(
                name='Google',
                industry='Technology',
                interests=['AI', 'cloud computing', 'digital advertising', 'machine learning', 'android', 'GCC tech initiatives', 'UAE tech innovation', 'Saudi digital transformation'],
                sources=[
                    # International sources
                    'https://techcrunch.com/category/google/',
                    'https://www.theverge.com/google',
                    'https://www.wired.com/tag/google/',
                    # GCC regional sources
                    'https://gulfbusiness.com/category/technology/',
                    'https://www.khaleejtimes.com/technology',
                    'https://arab.news/technology',
                    'https://smashi.tv/en/business',
                    # Government sources
                    'https://u.ae/en/about-the-uae/digital-uae/artificial-intelligence',
                    'https://ai.gov.ae/news-events/',
                    'https://www.vision2030.gov.sa/v2030/overview/'
                ]
            )
            logger.info(f"Created Google client with ID: {google_client.get('id')}")
        else:
            logger.info("Google client already exists")
        
        # Create Nestle client if it doesn't exist
        if 'Nestle' not in client_names:
            nestle_client = self.client_model.create_client(
                name='Nestle',
                industry='Food and Beverage',
                interests=['sustainable sourcing', 'consumer trends', 'nutrition', 'water management', 'food innovation', 'GCC food security', 'Saudi food sector', 'UAE food regulations'],
                sources=[
                    # International sources
                    'https://www.fooddive.com/topic/manufacturers/nestle/',
                    'https://www.foodnavigator.com/tag/keyword/Food/Nestle',
                    'https://www.just-food.com/tag/nestle/',
                    # GCC regional sources
                    'https://gulfbusiness.com/category/industry/food/',
                    'https://www.emirates247.com/business/corporate/food-beverage',
                    'https://www.arabianbusiness.com/industries/retail',
                    'https://smashi.tv/en/business',
                    # Government sources
                    'https://www.moccae.gov.ae/en/media-center/news.aspx',
                    'https://www.adafsa.gov.ae/English/News/Pages/default.aspx',
                    'https://sfda.gov.sa/en/news'
                ]
            )
            logger.info(f"Created Nestle client with ID: {nestle_client.get('id')}")
        else:
            logger.info("Nestle client already exists")
    
    def _crawl_client_sources(self, client: Dict[str, Any]):
        """Crawl the sources for a specific client to get the latest data with focus on GCC region."""
        logger.info(f"Crawling sources for {client.get('name')} with GCC focus")
        
        # GCC countries for filtering and tagging
        gcc_countries = ["UAE", "Saudi Arabia", "Qatar", "Kuwait", "Bahrain", "Oman"]
        gcc_keywords = ["Gulf", "GCC", "MENA", "Middle East", "Dubai", "Abu Dhabi", "Riyadh", "Doha", "Manama", "Muscat", "Kuwait City"]
        
        sources = client.get('sources', [])
        
        if sources:
            try:
                # Categorize sources by region priority
                gcc_sources = []
                gov_sources = []
                global_sources = []
                
                for source in sources:
                    domain = urlparse(source).netloc.lower()
                    if any(gcc_term.lower() in domain for gcc_term in ['gulf', 'gcc', 'arab', 'khaleejtimes', 'zawya', 'thenational']):
                        gcc_sources.append(source)
                    elif any(gov_term in domain for gov_term in ['.gov', '.gov.ae', '.gov.sa', '.gov.qa', '.gov.kw', '.gov.bh', '.gov.om']):
                        gov_sources.append(source)
                    else:
                        global_sources.append(source)
                
                # First crawl GCC-specific sources - these are highest priority
                if gcc_sources:
                    logger.info(f"Crawling {len(gcc_sources)} GCC-specific sources for {client.get('name')}")
                    self.crawler.crawl_sources_for_client(client.get('id'), gcc_sources)
                
                # Then crawl government sources
                if gov_sources:
                    logger.info(f"Crawling {len(gov_sources)} government sources for {client.get('name')}")
                    self.crawler.crawl_sources_for_client(client.get('id'), gov_sources)
                    
                # Finally crawl global sources but try to filter for GCC-related content
                if global_sources:
                    logger.info(f"Crawling {len(global_sources)} global sources for {client.get('name')}")
                    
                    # For global sources we'll try to filter for GCC content
                    # This is a simplified approach - ideally we would modify the crawler
                    # to accept filter keywords, but we're working with what we have
                    self.crawler.crawl_sources_for_client(client.get('id'), global_sources)
                    
                # Tag the articles with region info
                self._tag_articles_with_region(client.get('id'), gcc_countries, gcc_keywords)
                
                logger.info(f"Completed crawling all sources for {client.get('name')}")
                
            except Exception as e:
                logger.error(f"Error crawling sources for {client.get('name')}: {str(e)}")
        else:
            logger.warning(f"No sources defined for {client.get('name')}")
    
    def _tag_articles_with_region(self, client_id: str, gcc_countries: List[str], gcc_keywords: List[str]):
        """Tag articles with region information for better filtering."""
        # Get all client articles
        client_articles_key = f"client:{client_id}:articles"
        article_ids = self.redis_cache.get(client_articles_key) or []
        
        for article_id in article_ids:
            article_data = self.redis_cache.get(f"article:{article_id}")
            if not article_data:
                continue
                
            # Check if article is already tagged
            if 'region' in article_data:
                continue
                
            # Look for GCC mentions in the content
            content = article_data.get('content', '')
            title = article_data.get('title', '')
            description = article_data.get('description', '')
            
            # Combine all text fields for searching
            all_text = f"{title} {description} {content}".lower()
            
            # Check if any GCC country or keyword is mentioned
            is_gcc_related = False
            mentioned_regions = []
            
            for country in gcc_countries:
                if country.lower() in all_text:
                    is_gcc_related = True
                    mentioned_regions.append(country)
                    
            for keyword in gcc_keywords:
                if keyword.lower() in all_text:
                    is_gcc_related = True
                    mentioned_regions.append(keyword)
            
            # Tag the article
            if is_gcc_related:
                article_data['region'] = 'GCC'
                article_data['mentioned_regions'] = list(set(mentioned_regions))
                article_data['relevance_score'] = len(mentioned_regions) * 10  # Simple relevance score
            else:
                article_data['region'] = 'Global'
                article_data['relevance_score'] = 5  # Default score
            
            # Update the article in Redis
            self.redis_cache.set(f"article:{article_id}", article_data)
        
        logger.info(f"Tagged {len(article_ids)} articles with region information for client {client_id}")
    
    def get_client_by_name(self, client_name: str) -> Optional[Dict[str, Any]]:
        """Get a client by name.
        
        Args:
            client_name: The name of the client to look up
            
        Returns:
            The client dictionary if found, None otherwise
        """
        try:
            # Get all clients
            clients = self.client_model.get_all_clients()
            
            # Find client by name
            for client in clients:
                if client.get('name').lower() == client_name.lower():
                    return client
            
            logger.warning(f"Client not found: {client_name}")
            return None
        except Exception as e:
            logger.error(f"Error getting client by name: {str(e)}")
            return None
    
    def get_weekly_articles(self, client_id: str) -> List[Dict[str, Any]]:
        """Get articles from the past 7 days for a client, prioritizing GCC-specific content."""
        # Get all client articles
        client_articles_key = f"client:{client_id}:articles"
        article_ids = self.redis_cache.get(client_articles_key) or []
        
        # Current time and 7 days ago
        now = int(time.time())
        seven_days_ago = now - (7 * 24 * 60 * 60)  # 7 days in seconds
        
        # Filter articles by timestamp and collect region info
        weekly_articles = []
        gcc_articles = []
        global_articles = []
        
        for article_id in article_ids:
            article_data = self.redis_cache.get(f"article:{article_id}")
            if article_data:
                # Check if article is from the past 7 days
                article_time = article_data.get('timestamp', 0)
                if article_time >= seven_days_ago:
                    # Separate GCC and global articles
                    if article_data.get('region') == 'GCC':
                        gcc_articles.append(article_data)
                    else:
                        global_articles.append(article_data)
        
        # Sort GCC articles by relevance score in descending order
        gcc_articles.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Combine articles with GCC articles first
        weekly_articles = gcc_articles + global_articles
        
        # Log breakdown of articles
        logger.info(f"Found {len(weekly_articles)} articles from the past week for client {client_id}")
        logger.info(f"  - GCC-specific articles: {len(gcc_articles)}")
        logger.info(f"  - Global articles: {len(global_articles)}")
        
        return weekly_articles
    
    def generate_report_content(self, client: Dict[str, Any], articles: List[Dict[str, Any]]) -> str:
        """Generate report content using OpenAI based on client interests and articles, with GCC focus."""
        # If no articles, create a mock report for demonstration
        if not articles:
            logger.warning(f"No articles found for {client.get('name')}. Creating mock report.")
            
            # Create a basic report with no article data
            return f"""# Weekly Market Intelligence Report: {client.get('name')} - GCC Region Focus

## Report Period: {(datetime.now() - timedelta(days=7)).strftime('%B %d, %Y')} - {datetime.now().strftime('%B %d, %Y')}

### Executive Summary

Unfortunately, no relevant articles were found for {client.get('name')} in the Gulf Cooperation Council (GCC) region during the past week. This could be due to:

- Limited media coverage of {client.get('name')} in GCC publications
- Technical challenges in accessing regional news sources
- Temporary reduction in {client.get('name')}'s activities in the region

Our team is working to expand our data sources and improve our collection methods to ensure better coverage of GCC-related content in future reports.

## Recommendations

1. Consider adding additional regional news sources to monitor for {client.get('name')}
2. Expand the search terms to include local partners and subsidiaries in GCC countries
3. Consider extending the time range beyond one week for the next report to capture more regional activities

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # Extract client information
        client_name = client.get('name', 'Client')
        interests = client.get('interests', [])
        industry = client.get('industry', 'General')
        
        # Separate GCC and global articles
        gcc_articles = [a for a in articles if a.get('region') == 'GCC']
        global_articles = [a for a in articles if a.get('region') != 'GCC']
        
        # Prepare article data for the LLM, prioritizing GCC content
        article_data = "GCC-SPECIFIC ARTICLES:\n\n"
        
        # First add GCC articles
        for i, article in enumerate(gcc_articles[:10]):  # Limit to 10 GCC articles
            title = article.get('title', 'Untitled')
            summary = article.get('summary', article.get('description', 'No description available.'))
            url = article.get('url', '')
            regions = ", ".join(article.get('mentioned_regions', []))
            article_data += f"Article {i+1} [GCC - {regions}]: {title}\nSummary: {summary}\nURL: {url}\n\n"
        
        # Then add relevant global articles
        article_data += "\nGLOBAL ARTICLES WITH GCC RELEVANCE:\n\n"
        for i, article in enumerate(global_articles[:5]):  # Limit to 5 global articles
            title = article.get('title', 'Untitled')
            summary = article.get('summary', article.get('description', 'No description available.'))
            url = article.get('url', '')
            article_data += f"Article {i+1} [Global]: {title}\nSummary: {summary}\nURL: {url}\n\n"
        
        # Prepare the prompt based on client interests
        interests_text = ', '.join(interests) if interests else 'general market trends'
        
        try:
            # Generate the report content with GPT
            messages = [
                {"role": "system", "content": f"You are an expert market intelligence analyst specializing in {industry} with deep knowledge of the Gulf Cooperation Council (GCC) region. Your task is to generate a comprehensive weekly market intelligence report for {client_name}, focusing specifically on their interests in {interests_text} WITHIN THE GCC REGION. Be concise, data-driven, and focus on actionable insights specifically relevant to operations in Saudi Arabia, UAE, Qatar, Kuwait, Bahrain, and Oman."},
                {"role": "user", "content": f"""Based on the following recent articles, generate a GCC-focused market intelligence report for {client_name} centered on their interests in {interests_text} within the Gulf region.
                
                {article_data}
                
                Please structure the report exactly like the Google GAPP Media Roundup Brief with these guidelines:
                1. Title: GCC Market Intelligence Report for {client_name}
                2. Period: Include dates from {(datetime.now() - timedelta(days=7)).strftime('%B %d, %Y')} to {datetime.now().strftime('%B %d, %Y')}
                3. Executive Summary (2-3 paragraphs overview focusing on GCC impact)
                4. Main sections should be organized by relevant topics rather than countries
                5. Each bullet point must cite and summarize one source article with its URL in markdown link format
                6. Group related insights under appropriate headers (e.g., Digital Transformation, Sustainability Initiatives, etc.)
                7. Each point should connect the news to its relevance for {client_name}'s business
                8. Ensure full traceability and credibility by always citing sources
                
                CRITICAL INSTRUCTION: For each bullet point, you MUST use the EXACT article URL that is provided in the "URL:" field of the corresponding article data above. DO NOT use general section URLs (like https://www.website.com/section/) or homepage URLs. Instead, use the complete, specific article URLs exactly as provided in the article data (like https://www.website.com/section/specific-article-title). This is essential for proper citation and traceability.
                
                The report should emphasize implications for {client_name}'s business in the GCC region.
                Use markdown formatting for the report structure.
                Include source URLs in a hyperlinked format for each bullet point.
                Make sure each insight includes a URL citation.
                The report should cover the period from {(datetime.now() - timedelta(days=7)).strftime('%B %d, %Y')} to {datetime.now().strftime('%B %d, %Y')}.
                """}
            ]
            
            response = self.openai_client.create_chat_completion(
                messages=messages,
                temperature=0.4,
                max_tokens=2000
            )
            
            # Extract the report content
            report_content = response.choices[0].message.content.strip()
            
            # Post-process the report to enforce correct URLs
            report_content = self._enforce_correct_urls(report_content, articles)
            
            # Add a header and footer if not present
            if not report_content.startswith("#"):
                report_title = f"# Weekly GCC Market Intelligence Report: {client_name}"
                report_content = f"{report_title}\n\n{report_content}"
                
            # Add generation date at the bottom if not present
            generation_info = f"\n\n---\n\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            if "Generated on:" not in report_content:
                report_content += generation_info
                
            return report_content
            
        except Exception as e:
            logger.error(f"Error generating report with LLM: {str(e)}")
            
            # Fallback to template-based report
            report_title = f"# Weekly GCC Market Intelligence Report: {client_name}"
            report_date = f"## Report Period: {(datetime.now() - timedelta(days=7)).strftime('%B %d, %Y')} - {datetime.now().strftime('%B %d, %Y')}"
            
            # Separate sections for GCC and global content
            gcc_section = "## GCC Region Articles\n\n"
            for article in gcc_articles[:5]:  # Limit to 5 GCC articles
                title = article.get('title', 'Untitled')
                url = article.get('url', '#')  # Use the specific article URL
                summary = article.get('summary', article.get('description', 'No description available.'))
                regions = ", ".join(article.get('mentioned_regions', ["GCC"]))
                gcc_section += f"### [{title}]({url}) - {regions}\n\n{summary}\n\n---\n\n"
            
            global_section = "## Global Articles with GCC Relevance\n\n"
            for article in global_articles[:3]:  # Limit to 3 global articles
                title = article.get('title', 'Untitled')
                url = article.get('url', '#')  # Use the specific article URL
                summary = article.get('summary', article.get('description', 'No description available.'))
                global_section += f"### [{title}]({url})\n\n{summary}\n\n---\n\n"
            
            interests_section = f"## Strategic Focus Areas for GCC\n\n{interests_text}\n\n"
            
            footer = f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            report_content = f"{report_title}\n\n{report_date}\n\n{gcc_section}{global_section}{interests_section}{footer}"
            
            # Apply the same URL enforcement to the template-based report
            report_content = self._enforce_correct_urls(report_content, articles)
            
            return report_content
    
    def _enforce_correct_urls(self, report_content: str, articles: List[Dict[str, Any]]) -> str:
        """
        Enforce that URLs in the report match the actual article URLs.
        This is a fallback in case the LLM still uses general section URLs.
        
        Args:
            report_content: The generated report content
            articles: List of article data
            
        Returns:
            Updated report content with correct URLs
        """
        logger.info("Enforcing correct article URLs in the report")
        
        # Create a list of actual article URLs with their article data
        article_urls = {article.get('url', ''): article for article in articles if article.get('url')}
        
        # Log the actual article URLs we have
        logger.info(f"Available article URLs: {list(article_urls.keys())}")
        
        # Create a map of domain to article URLs for that domain
        domain_to_articles = {}
        for url, article in article_urls.items():
            try:
                domain = urlparse(url).netloc
                if domain not in domain_to_articles:
                    domain_to_articles[domain] = []
                domain_to_articles[domain].append((url, article))
            except Exception:
                pass
        
        # Find all markdown links in the report
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        matches = re.findall(link_pattern, report_content)
        
        # Log the URLs found in the report
        logger.info(f"URLs found in report: {[url for _, url in matches]}")
        
        # Dictionary to track replacements
        replacements = {}
        
        # For each domain, find and replace all links to that domain
        for domain, domain_articles in domain_to_articles.items():
            if not domain_articles:
                continue
                
            # Get the URLs for this domain
            domain_urls = [url for url, _ in domain_articles]
            
            # Find all links to this domain in the report
            domain_links = [link_url for _, link_url in matches if domain in link_url]
            
            # If we have links to this domain in the report
            if domain_links:
                for link_url in domain_links:
                    # If the link URL is not an exact match to one of our article URLs
                    if link_url not in domain_urls:
                        # Replace it with the first article URL for this domain
                        correct_url = domain_urls[0]
                        replacements[link_url] = correct_url
                        logger.warning(f"Will replace generic URL {link_url} with specific article URL {correct_url}")
        
        # Apply all replacements
        for old_url, new_url in replacements.items():
            report_content = report_content.replace(f']({old_url})', f']({new_url})')
            logger.info(f"Replaced URL: {old_url} → {new_url}")
        
        # Special case: If we have section headers containing "Source" or "Read more", make sure those links are replaced too
        source_pattern = r'Source[^\[]*\[([^\]]+)\]\(([^)]+)\)'
        read_more_pattern = r'Read more[^\[]*\[([^\]]+)\]\(([^)]+)\)'
        
        for pattern in [source_pattern, read_more_pattern]:
            source_matches = re.findall(pattern, report_content, re.IGNORECASE)
            for _, link_url in source_matches:
                for domain, domain_articles in domain_to_articles.items():
                    if domain in link_url and link_url not in [url for url, _ in domain_articles]:
                        correct_url = domain_articles[0][0]
                        report_content = report_content.replace(f']({link_url})', f']({correct_url})')
                        logger.info(f"Replaced source link: {link_url} → {correct_url}")
        
        # Direct replacement approach for specific patterns
        # Replace common generic URLs with specific article URLs
        for domain in domain_to_articles:
            # If we have articles for this domain
            if domain_to_articles[domain]:
                # Get the specific article URL to use as replacement
                specific_url = domain_to_articles[domain][0][0]
                
                # Look for markdown links with this domain that might be general section URLs
                section_patterns = [
                    f"(\\[.*?\\]\\()https?://{domain}/[^)]*?(\\))",  # General pattern
                    f"(\\[.*?\\]\\()https?://{domain}/category/[^)]*?(\\))",  # Category pattern
                    f"(\\[.*?\\]\\()https?://{domain}/tag/[^)]*?(\\))",  # Tag pattern
                ]
                
                for pattern in section_patterns:
                    # Replace all instances with the specific article URL
                    report_content = re.sub(pattern, f"\\1{specific_url}\\2", report_content)
        
        # Log the final URLs in the report
        final_matches = re.findall(link_pattern, report_content)
        logger.info(f"Final URLs in report: {[url for _, url in final_matches]}")
        
        return report_content
    
    def save_markdown_report(self, client_name: str, content: str) -> str:
        """Save report content as a markdown file."""
        # Clean client name for filename
        clean_name = client_name.lower().replace(' ', '-')
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"{clean_name}-weekly-report-{timestamp}.md"
        filepath = os.path.join(self.reports_dir, filename)
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Saved markdown report to {filepath}")
        return filepath
    
    def generate_pdf_from_markdown(self, markdown_path: str, client_name: str) -> Optional[str]:
        """Generate a PDF from the markdown report with GCC-specific styling."""
        import markdown
        from weasyprint import HTML
        
        # Clean client name for filename
        clean_name = client_name.lower().replace(' ', '-')
        
        # Get timestamp from markdown filename
        filename = os.path.basename(markdown_path)
        timestamp = filename.split('-')[-1].split('.')[0]
        
        # Create PDF filename
        pdf_filename = f"{clean_name}-gcc-report-{timestamp}.pdf"
        pdf_filepath = os.path.join(self.reports_dir, pdf_filename)
        
        try:
            # Read markdown content
            with open(markdown_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            # Convert markdown to HTML
            html_content = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
            
            # Add CSS styling with GCC-specific color scheme and branding
            styled_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>{client_name} - GCC Weekly Intelligence Report</title>
                <style>
                    body {{ 
                        font-family: Arial, sans-serif; 
                        line-height: 1.6; 
                        max-width: 900px; 
                        margin: 0 auto; 
                        padding: 20px;
                        color: #333;
                    }}
                    h1 {{ 
                        color: #005b82; /* GCC blue */ 
                        border-bottom: 3px solid #00a78e; /* Teal accent */
                        padding-bottom: 10px;
                    }}
                    h2 {{ 
                        color: #00a78e; /* Teal - used in many GCC brand guidelines */
                        border-bottom: 1px solid #eee; 
                        padding-bottom: 5px; 
                    }}
                    h3 {{ color: #007c59; /* Darker teal */ }}
                    h4 {{ color: #d4a017; /* Gold accent - common in GCC styling */ }}
                    a {{ color: #005b82; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                    th, td {{ text-align: left; padding: 12px; }}
                    th {{ background-color: #005b82; color: white; }}
                    tr:nth-child(even) {{ background-color: #f2f2f2; }}
                    img {{ max-width: 100%; height: auto; }}
                    .date {{ color: #7f8c8d; font-size: 0.9em; }}
                    blockquote {{ 
                        background-color: #f9f9f9; 
                        border-left: 5px solid #00a78e; 
                        margin: 1.5em 10px; 
                        padding: 0.5em 10px; 
                    }}
                    .header {{ 
                        text-align: center; 
                        margin-bottom: 30px;
                        padding: 20px;
                        background: linear-gradient(to right, #005b82, #00a78e);
                        color: white;
                        border-radius: 5px;
                    }}
                    .header h1 {{ 
                        color: white; 
                        border-bottom: none;
                        margin-bottom: 5px;
                    }}
                    .header p {{ 
                        color: rgba(255, 255, 255, 0.8);
                    }}
                    .footer {{ 
                        text-align: center; 
                        margin-top: 30px; 
                        padding: 15px;
                        font-size: 0.9em; 
                        color: #666;
                        border-top: 1px solid #00a78e;
                    }}
                    .gcc-tag {{
                        display: inline-block;
                        background-color: #00a78e;
                        color: white;
                        padding: 3px 8px;
                        border-radius: 3px;
                        font-size: 0.8em;
                        margin-right: 5px;
                    }}
                    .global-tag {{
                        display: inline-block;
                        background-color: #005b82;
                        color: white;
                        padding: 3px 8px;
                        border-radius: 3px;
                        font-size: 0.8em;
                        margin-right: 5px;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>{client_name} - GCC Market Intelligence Report</h1>
                    <p class="date">{(datetime.now() - timedelta(days=7)).strftime('%B %d, %Y')} - {datetime.now().strftime('%B %d, %Y')}</p>
                </div>
                
                {html_content}
                
                <div class="footer">
                    <p>Generated by Global Possibilities Market Intelligence Platform</p>
                    <p>Confidential - For internal use only</p>
                    <p>Gulf Cooperation Council Regional Focus</p>
                </div>
            </body>
            </html>
            """
            
            # Generate PDF using WeasyPrint
            HTML(string=styled_html).write_pdf(pdf_filepath)
            logger.info(f"Generated PDF report at {pdf_filepath}")
            return pdf_filepath
            
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            return None
    
    def generate_client_report(self, client_name: str, output_format: str = 'both') -> Optional[str]:
        """Generate a complete weekly report for a client by name.
        
        Args:
            client_name: The name of the client to generate a report for
            output_format: Format to generate ('markdown', 'pdf', or 'both')
            
        Returns:
            Path to the generated markdown file if successful, None otherwise
        """
        # Get the client by name
        client = self.get_client_by_name(client_name)
        if not client:
            logger.error(f"Client {client_name} not found")
            return None
        
        # Get the client ID
        client_id = client.get('id')
        if not client_id:
            logger.error(f"Client {client_name} has no ID")
            return None
        
        # Crawl sources for latest data if not simulating
        if not self.simulate_crawling:
            self._crawl_client_sources(client)
        
        # Get weekly articles
        articles = self.get_weekly_articles(client_id)
        article_count = len(articles) if articles else 0
        logger.info(f"Found {article_count} articles for {client_name}")
        
        # Generate report content
        report_content = self.generate_report_content(client, articles)
        if not report_content:
            logger.error(f"Failed to generate report content for {client_name}")
            return None
        
        # Save as markdown
        md_path = self.save_markdown_report(client_name, report_content)
        logger.info(f"Saved markdown report to {md_path}")
        
        # Generate PDF if requested
        pdf_path = None
        if output_format in ['pdf', 'both']:
            pdf_path = self.generate_pdf_from_markdown(md_path, client_name)
            if pdf_path:
                logger.info(f"Generated PDF report at {pdf_path}")
            else:
                logger.error(f"Failed to generate PDF for {client_name}")
        
        # Return the markdown path as confirmation of success
        return md_path

def main():
    """Run the report generation process."""
    parser = argparse.ArgumentParser(description='Generate market intelligence reports for clients with GCC focus')
    parser.add_argument('--client', type=str, help='Client name to generate report for (Google or Nestle)', choices=['Google', 'Nestle'])
    parser.add_argument('--output-dir', type=str, help='Directory to save reports', default='reports')
    parser.add_argument('--days', type=int, help='Number of days to look back for articles', default=7)
    parser.add_argument('--format', type=str, help='Output format', choices=['markdown', 'pdf', 'both'], default='both')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--simulate', action='store_true', help='Simulate crawling (use cached data if available)')
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'report_generation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    
    # Initialize the report generator
    generator = ClientReportGenerator(
        reports_dir=args.output_dir,
        lookback_days=args.days,
        simulate_crawling=args.simulate
    )

    # Create Google and Nestle clients if they don't exist
    generator._create_specific_clients()
    
    # Process specific client or both
    if args.client:
        logger.info(f"Generating report for {args.client}")
        
        # Get the client
        client = generator.get_client_by_name(args.client)
        if not client:
            print(f"Client {args.client} not found. Please check the client name.")
            return

        # Generate the report
        md_path = generator.generate_client_report(args.client, args.format)
        if md_path:
            logger.info(f"Successfully generated report for {args.client}")
            print(f"Report generated for {args.client}. Files saved to {args.output_dir} directory.")
    else:
        # Generate for both clients
        success = []
        for client_name in ["Google", "Nestle"]:
            logger.info(f"Generating report for {client_name}")
            
            # Get the client
            client = generator.get_client_by_name(client_name)
            if not client:
                print(f"Client {client_name} not found. Skipping.")
                continue
                
            # Generate the report
            md_path = generator.generate_client_report(client_name, args.format)
            if md_path:
                success.append(client_name)
                logger.info(f"Successfully generated report for {client_name}")
        
        if success:
            print(f"Reports generated for: {', '.join(success)}. Files saved to {args.output_dir} directory.")
        else:
            print("No reports were successfully generated.")


if __name__ == "__main__":
    main() 